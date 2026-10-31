"""Integration tests against PostgreSQL, isolated in a disposable schema.
Run from the application directory: python -m unittest discover -s tests -v
"""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg2
from psycopg2 import sql
from werkzeug.security import generate_password_hash

SCHEMA = 'test_reservations_' + uuid.uuid4().hex
connection = psycopg2.connect(user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'))
connection.autocommit = True
with connection.cursor() as cursor:
    cursor.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(SCHEMA)))
os.environ['PGOPTIONS'] = '-c search_path=' + SCHEMA
from app import app  # noqa: E402
from api.sql import DB  # noqa: E402


def tearDownModule():
    DB.connection_pool.closeall()
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(SCHEMA)))
    connection.close()


class ReservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True, SECRET_KEY='test-only-secret')
        cls.runner = app.test_cli_runner()
        result = cls.runner.invoke(args=['init-reservations'])
        assert result.exit_code == 0, result.output

    def setUp(self):
        conn = DB.connect()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute('TRUNCATE usage_record, reservation_audit, reservation, venue_equipment, venue, app_user RESTART IDENTITY CASCADE')
                for uid, role in [('MANAGER','manager'), ('STUDENT','student'), ('TEACHER','teacher')]:
                    cursor.execute('''INSERT INTO app_user
                        (uid,user_name,password_hash,identity,email,did)
                        VALUES (%s,%s,%s,%s,%s,'GENERAL')''',
                        (uid, uid, generate_password_hash('test-password-123'), role, uid+'@example.test'))
        DB.release(conn)
        self.venue_id = self.venue('A101')
        self.client = app.test_client()
        self.login('MANAGER')

    def token(self, client=None):
        client = client or self.client
        client.get('/login')
        with client.session_transaction() as session:
            return session['_csrf_token']

    def login(self, uid, client=None):
        client = client or self.client
        return client.post('/login', data={'uid':uid, 'password':'test-password-123',
            'csrf_token': self.token(client)})

    def post(self, path, data=None, client=None):
        client = client or self.client
        return client.post(path, data={**(data or {}), 'csrf_token': self.token(client)})

    def venue(self, name='A101', capacity=40, status='open'):
        conn = DB.connect()
        with conn:
            with conn.cursor() as cur:
                cur.execute('SELECT vid FROM venue WHERE lower(venue_name)=lower(%s)', (name,))
                row = cur.fetchone()
                if row:
                    vid = row[0]
                else:
                    cur.execute("INSERT INTO venue(venue_name,venue_type,capacity,status) VALUES(%s,'教室',%s,%s) RETURNING vid", (name,capacity,status))
                    vid = cur.fetchone()[0]
        DB.release(conn)
        return vid

    def create(self, **changes):
        data = dict(applicant_uid='STUDENT', venue_id=self.venue_id, starts_at='2099-11-10T09:00',
            ends_at='2099-11-10T10:00', purpose='課程活動', attendees='20')
        if 'venue' in changes:
            changes['venue_id'] = self.venue(changes.pop('venue'))
        data.update(changes)
        result = self.post('/admin/reservations/new', data)
        self.assertEqual(result.status_code, 302)
        return int(result.location.rsplit('/',1)[1])

    def row(self, rid):
        conn = DB.connect()
        with conn.cursor() as cursor:
            cursor.execute('SELECT status, version, deleted_at FROM reservation WHERE id=%s', (rid,))
            result = cursor.fetchone()
        conn.rollback()
        DB.release(conn)
        return result

    def review(self, rid, decision='approved', note='', version=None):
        return self.post(f'/admin/reservations/{rid}/review',
            dict(decision=decision, review_note=note, version=version or self.row(rid)[1]))

    def test_crud_review_and_audit(self):
        rid = self.create()
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}').status_code, 200)
        result = self.post(f'/admin/reservations/{rid}/edit', dict(applicant_uid='STUDENT',
            venue_id=self.venue_id, starts_at='2099-11-10T10:00', ends_at='2099-11-10T11:00',
            purpose='改期', attendees='10', version='1'))
        self.assertEqual(result.status_code,302)
        self.assertEqual(self.row(rid)[:2],('pending',2))
        self.assertEqual(self.review(rid).status_code,302)
        self.assertEqual(self.row(rid)[:2],('approved',3))
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}').status_code,200)
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}/edit').status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/edit',{}).status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/delete',{'version':3}).status_code,302)
        self.assertIsNotNone(self.row(rid)[2])
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}').status_code,404)
        conn = DB.connect()
        with conn.cursor() as cur:
            cur.execute('SELECT action FROM reservation_audit WHERE reservation_id=%s ORDER BY id', (rid,))
            self.assertEqual([r[0] for r in cur.fetchall()],['create','edit','approved','delete'])
        conn.rollback()
        DB.release(conn)

    def test_roles_and_anonymous_access(self):
        rid = self.create()
        for uid in ('STUDENT','TEACHER',None):
            client = app.test_client()
            if uid:
                self.login(uid,client)
            for path in ('/admin/home','/admin/dashboard','/admin/reservations',
                         '/admin/reservations/new','/admin/venues','/admin/venues/new',f'/admin/reservations/{rid}',f'/admin/reservations/{rid}/edit'):
                self.assertEqual(client.get(path).status_code,403 if uid else 302)
            for path in ('/admin/reservations/new',f'/admin/reservations/{rid}/edit',
                         f'/admin/reservations/{rid}/delete',f'/admin/reservations/{rid}/review',
                         f'/admin/reservations/{rid}/cancel',f'/admin/reservations/{rid}/usage',
                         f'/admin/reservations/{rid}/usage/delete','/admin/venues/new'):
                self.assertEqual(self.post(path,client=client).status_code,403 if uid else 302)

    def test_csrf_and_post_only(self):
        rid = self.create()
        for path in ('/admin/reservations/new',f'/admin/reservations/{rid}/edit',
                     f'/admin/reservations/{rid}/delete',f'/admin/reservations/{rid}/review',
                         f'/admin/reservations/{rid}/cancel',f'/admin/reservations/{rid}/usage',
                         f'/admin/reservations/{rid}/usage/delete','/admin/venues/new'):
            self.assertEqual(self.client.post(path).status_code,400)
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}/delete').status_code,405)
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}/review').status_code,405)
        self.assertEqual(self.client.post('/admin/reservations/new', data={'csrf_token':'錯誤'}).status_code,400)
        self.assertEqual(self.row(rid)[:2],('pending',1))

    def test_overlap_and_adjacent_times(self):
        first = self.create()
        second = self.create(venue='a101')
        self.review(first)
        response = self.review(second)
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.row(second)[0],'pending')
        self.assertIn('已有核准預約',self.client.get(response.location).get_data(as_text=True))
        third = self.create(starts_at='2099-11-10T10:00',ends_at='2099-11-10T11:00')
        self.review(third)
        self.assertEqual(self.row(third)[0],'approved')
        self.assertEqual(self.post('/admin/reservations/new', dict(applicant_uid='STUDENT',
            venue_id=self.venue_id, starts_at='2099-11-10T09:30',ends_at='2099-11-10T10:30',
            purpose='conflict',attendees=1)).status_code,400)

    def test_stale_updates_and_repeated_reviews(self):
        rid = self.create()
        self.review(rid)
        self.assertEqual(self.review(rid,version=1).status_code,409)
        self.assertEqual(self.review(rid,version=2).status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/delete',{'version':1}).status_code,409)
        self.assertEqual(self.row(rid)[:2],('approved',2))

    def test_validation_and_rejection_reason(self):
        data = dict(applicant_uid='STUDENT',venue_id=self.venue_id,starts_at='2099-11-10T09:00',
            ends_at='2099-11-10T10:00',purpose='活動',attendees=1)
        for change in ({'ends_at':'2099-11-10T08:00'},{'starts_at':'invalid'},
                       {'applicant_uid':'MISSING'},{'purpose':' '},{'attendees':'-1'},
                       {'venue_id':'-1'},{'attendees':'abc'}):
            self.assertEqual(self.post('/admin/reservations/new',{**data,**change}).status_code,400)
        rid = self.create()
        self.review(rid,'rejected','')
        self.assertEqual(self.row(rid)[0],'pending')
        self.assertEqual(self.review(rid,'bogus').status_code,400)
        self.assertEqual(self.client.get('/admin/reservations?from=bad').status_code,400)
        self.assertEqual(self.client.get('/admin/reservations?status=bogus').status_code,400)

    def test_dashboard_filters_and_escaping(self):
        rid = self.create(venue='<script>alert(1)</script>')
        self.review(rid)
        self.create(venue='Other')
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code,200)
        text = response.get_data(as_text=True)
        self.assertIn('近六個月預約趨勢',text)
        self.assertIn('&lt;script&gt;',text)
        self.assertNotIn('<script>alert(1)</script>',text)
        response = self.client.get('/admin/reservations?status=approved&q=script&from=2099-11-10&to=2099-11-10')
        self.assertEqual(response.status_code,200)
        self.assertIn('共 1 筆',response.get_data(as_text=True))
        response = self.client.get('/admin/reservations?q=%27%20OR%201=1--')
        self.assertIn('共 0 筆',response.get_data(as_text=True))
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}/edit').status_code,409)

    def test_register_does_not_grant_manager(self):
        client = app.test_client()
        self.assertEqual(client.get('/register').status_code,200)
        response = self.post('/register',dict(uid='NEWUSER',username='新使用者',email='new@example.test',
            password='test-password-123',did='GENERAL',phone='',identity='manager'),client=client)
        self.assertEqual(response.status_code,302)
        self.login('NEWUSER',client)
        self.assertEqual(client.get('/admin/dashboard').status_code,403)
        self.assertEqual(client.get('/user/home').status_code,200)

    def test_manager_cli_and_repeatable_migration(self):
        result = self.runner.invoke(args=['init-reservations'])
        self.assertEqual(result.exit_code,0,result.output)
        result = self.runner.invoke(args=['create-manager','--uid','ADMIN2','--name','管理者',
            '--email','admin2@example.test'],input='strong-password-123\nstrong-password-123\n')
        self.assertEqual(result.exit_code,0,result.output)
        duplicate = self.runner.invoke(args=['create-manager','--uid','ADMIN2','--name','管理者',
            '--email','admin3@example.test'],input='strong-password-123\nstrong-password-123\n')
        self.assertNotEqual(duplicate.exit_code,0)

    def test_simultaneous_approvals_cannot_double_book(self):
        first, second = self.create(), self.create()
        barrier = Barrier(2)

        def approve(rid):
            client = app.test_client()
            self.login('MANAGER', client)
            token = self.token(client)
            barrier.wait(timeout=5)
            return client.post(f'/admin/reservations/{rid}/review', data={
                'csrf_token':token, 'version':'1', 'decision':'approved'}).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(list(executor.map(approve, (first, second))), [302,302])
        self.assertEqual(sorted([self.row(first)[0], self.row(second)[0]]), ['approved','pending'])

    def test_rejected_reservation_is_immutable(self):
        rid = self.create()
        self.review(rid,'rejected','設備維修')
        self.assertEqual(self.row(rid)[:2],('rejected',2))
        self.assertEqual(self.client.get(f'/admin/reservations/{rid}/edit').status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/edit',{}).status_code,409)
        self.assertEqual(self.review(rid,version=2).status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/cancel',{'version':2}).status_code,409)
        self.assertNotEqual(self.create(),rid)

    def test_venue_capacity_status_and_equipment_crud(self):
        response = self.post('/admin/venues/new',dict(venue_name='討論室',venue_type='討論室',
            capacity=8,status='open',description='請保持安靜',equipment='投影機 | 正常 | 1\n麥克風 | 故障 | 2'))
        self.assertEqual(response.status_code,302)
        vid = int(response.location.rsplit('/',1)[1])
        self.assertIn('投影機',self.client.get(response.location).get_data(as_text=True))
        self.assertEqual(self.client.get('/admin/venues').status_code,200)
        self.assertEqual(self.client.get(f'/admin/venues/{vid}/edit').status_code,200)
        self.assertEqual(self.post(f'/admin/venues/{vid}/edit',dict(venue_name='討論室',venue_type='討論室',
            capacity=8,status='open',equipment='白板 | 正常 | 1')).status_code,302)
        text = self.client.get(f'/admin/venues/{vid}').get_data(as_text=True)
        self.assertIn('白板',text)
        self.assertNotIn('投影機',text)
        data = dict(applicant_uid='STUDENT',venue_id=vid,starts_at='2099-11-10T09:00',
            ends_at='2099-11-10T10:00',purpose='討論',attendees=9)
        self.assertEqual(self.post('/admin/reservations/new',data).status_code,400)
        closed = self.venue('維修場地',status='maintenance')
        self.assertEqual(self.post('/admin/reservations/new',{**data,'venue_id':closed,'attendees':1}).status_code,400)
        rid = self.create(venue_id=vid,attendees=5)
        self.review(rid)
        self.assertEqual(self.post(f'/admin/venues/{vid}/delete').status_code,409)
        self.assertEqual(self.post(f'/admin/venues/{vid}/edit',dict(venue_name='討論室',venue_type='討論室',
            capacity=3,status='open')).status_code,400)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/cancel',{'version':2}).status_code,302)
        self.assertEqual(self.row(rid)[0],'cancelled')
        self.assertEqual(self.post(f'/admin/venues/{vid}/delete').status_code,302)
        self.assertEqual(self.client.get(f'/admin/venues/{vid}').status_code,404)

    def test_usage_weak_entity_and_cancel_rules(self):
        rid = self.create()
        data = dict(start_time='2099-11-10T09:03',end_time='',comment='到場',version=1)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/usage',data).status_code,409)
        self.review(rid)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/usage',{**data,'version':2}).status_code,302)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/usage',{
            **data,'version':3,'end_time':'2099-11-10T10:02','comment':'器材故障'}).status_code,302)
        self.assertIn('器材故障',self.client.get(f'/admin/reservations/{rid}').get_data(as_text=True))
        conn = DB.connect()
        with conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM usage_record WHERE rid=%s',(rid,))
            self.assertEqual(cur.fetchone()[0],1)
        conn.rollback()
        DB.release(conn)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/cancel',{'version':4}).status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/delete',{'version':4}).status_code,409)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/usage/delete',{'version':4}).status_code,302)
        self.assertEqual(self.post(f'/admin/reservations/{rid}/cancel',{'version':5}).status_code,302)
        self.assertEqual(self.review(rid,version=6).status_code,409)

    def test_pagination_and_missing_record(self):
        for i in range(21):
            self.create(venue=f'Room {i}')
        result = self.client.get('/admin/reservations?page=2').get_data(as_text=True)
        self.assertIn('2 / 2 頁',result)
        self.assertEqual(self.client.get('/admin/reservations/999999').status_code,404)


if __name__ == '__main__':
    unittest.main()
