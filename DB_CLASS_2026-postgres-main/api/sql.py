
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from psycopg2.extras import RealDictCursor
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv


# ==========================================
# PostgreSQL 資料庫連線設定
# ==========================================

load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '.env'
    )
)

USER = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')
DBNAME = os.getenv('DB_NAME')
HOST = os.getenv('DB_HOST')
PORT = os.getenv('DB_PORT')


# ==========================================
# 資料庫操作類別
# ==========================================

class DB:

    connection_pool = pool.ThreadedConnectionPool(
        1, 100,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )

    @staticmethod
    def connect():
        return DB.connection_pool.getconn()

    @staticmethod
    def release(connection):
        DB.connection_pool.putconn(connection)

    @staticmethod
    def execute_input(sql, input_data):

        if not isinstance(input_data, (tuple, list)):
            raise TypeError(
                "Input should be a tuple or list"
            )

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, input_data)

            connection.commit()

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error executing SQL: {e}")
            raise

        finally:
            DB.release(connection)

    @staticmethod
    def execute(sql):

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)

            connection.commit()

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error executing SQL: {e}")
            raise

        finally:
            DB.release(connection)

    @staticmethod
    def fetchall(sql, input_data=None):

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, input_data)
                result = cursor.fetchall()

            connection.rollback()
            return result

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error fetching data: {e}")
            raise

        finally:
            DB.release(connection)

    @staticmethod
    def fetchone(sql, input_data=None):

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, input_data)
                result = cursor.fetchone()

            connection.rollback()
            return result

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error fetching data: {e}")
            raise

        finally:
            DB.release(connection)


# ==========================================
# 系所資料
# ==========================================

class Department:

    @staticmethod
    def get_all():

        sql = """
            SELECT did, dname
            FROM department
            ORDER BY dname
        """

        return DB.fetchall(sql)


# ==========================================
# 校園系統使用者
# ==========================================

class AppUser:

    # 使用 UID 查詢帳號
    @staticmethod
    def get_user(uid):

        sql = """
            SELECT
                uid,
                user_name,
                password_hash,
                identity,
                email,
                phone,
                did
            FROM app_user
            WHERE uid = %s
        """

        return DB.fetchone(sql, (uid,))

    # 取得使用者身分與姓名
    @staticmethod
    def get_role(uid):

        sql = """
            SELECT
                identity,
                user_name
            FROM app_user
            WHERE uid = %s
        """

        return DB.fetchone(sql, (uid,))

    # 檢查 Email 是否重複
    @staticmethod
    def get_user_by_email(email):

        sql = """
            SELECT uid
            FROM app_user
            WHERE email = %s
        """

        return DB.fetchone(sql, (email,))

    # 註冊新使用者
    @staticmethod
    def create_user(input_data):

        sql = """
            INSERT INTO app_user
            (
                uid,
                user_name,
                password_hash,
                identity,
                email,
                phone,
                did
            )
            VALUES
            (
                %s, %s, %s, %s,
                %s, %s, %s
            )
        """

        DB.execute_input(sql, (
            input_data['uid'],
            input_data['user_name'],
            input_data['password_hash'],
            'student',
            input_data['email'],
            input_data['phone'],
            input_data['did']
        ))


# ==========================================
# 原始書店系統：會員
# ==========================================

class Member:

    @staticmethod
    def get_member(account):

        sql = """
            SELECT account, password, mid,
                   identity, name
            FROM member
            WHERE account = %s
        """

        return DB.fetchall(sql, (account,))

    @staticmethod
    def get_all_account():

        sql = "SELECT account FROM member"

        return DB.fetchall(sql)

    @staticmethod
    def create_member(input_data):

        sql = """
            INSERT INTO member
            (name, account, password, identity)
            VALUES (%s, %s, %s, %s)
        """

        DB.execute_input(sql, (
            input_data['name'],
            input_data['account'],
            input_data['password'],
            input_data['identity']
        ))

    @staticmethod
    def delete_product(tno, pid):

        sql = """
            DELETE FROM record
            WHERE tno = %s AND pid = %s
        """

        DB.execute_input(sql, (tno, pid))

    @staticmethod
    def get_order(userid):

        sql = """
            SELECT *
            FROM order_list
            WHERE mid = %s
            ORDER BY ordertime DESC
        """

        return DB.fetchall(sql, (userid,))

    @staticmethod
    def get_role(userid):

        sql = """
            SELECT identity, name
            FROM member
            WHERE mid = %s
        """

        return DB.fetchone(sql, (userid,))


# ==========================================
# 原始書店系統：購物車
# ==========================================

class Cart:

    @staticmethod
    def check(user_id):

        sql = """
            SELECT *
            FROM cart, record
            WHERE cart.mid = %s::bigint
              AND cart.tno = record.tno::bigint
        """

        return DB.fetchone(sql, (user_id,))

    @staticmethod
    def get_cart(user_id):

        sql = """
            SELECT *
            FROM cart
            WHERE mid = %s
        """

        return DB.fetchone(sql, (user_id,))

    @staticmethod
    def add_cart(user_id, time):

        sql = """
            INSERT INTO cart
            (mid, carttime, tno)
            VALUES (%s, %s, nextval('cart_tno_seq'))
        """

        DB.execute_input(sql, (user_id, time))

    @staticmethod
    def clear_cart(user_id):

        sql = """
            DELETE FROM cart
            WHERE mid = %s
        """

        DB.execute_input(sql, (user_id,))


# ==========================================
# 原始書店系統：商品
# ==========================================

class Product:

    @staticmethod
    def count():

        sql = "SELECT COUNT(*) FROM product"

        return DB.fetchone(sql)

    @staticmethod
    def get_product(pid):

        sql = """
            SELECT *
            FROM product
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))

    @staticmethod
    def get_all_product():

        sql = "SELECT * FROM product"

        return DB.fetchall(sql)

    @staticmethod
    def get_name(pid):

        sql = """
            SELECT pname
            FROM product
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))[0]

    @staticmethod
    def add_product(input_data):

        sql = """
            INSERT INTO product
            (pid, pname, price, category, pdesc)
            VALUES (%s, %s, %s, %s, %s)
        """

        DB.execute_input(sql, (
            input_data['pid'],
            input_data['pname'],
            input_data['price'],
            input_data['category'],
            input_data['pdesc']
        ))

    @staticmethod
    def delete_product(pid):

        sql = """
            DELETE FROM product
            WHERE pid = %s
        """

        DB.execute_input(sql, (pid,))

    @staticmethod
    def update_product(input_data):

        sql = """
            UPDATE product
            SET pname = %s,
                price = %s,
                category = %s,
                pdesc = %s
            WHERE pid = %s
        """

        DB.execute_input(sql, (
            input_data['pname'],
            input_data['price'],
            input_data['category'],
            input_data['pdesc'],
            input_data['pid']
        ))


# ==========================================
# 原始書店系統：購買紀錄
# ==========================================

class Record:

    @staticmethod
    def get_total_money(tno):

        sql = """
            SELECT SUM(total)
            FROM record
            WHERE tno = %s
        """

        return DB.fetchone(sql, (tno,))[0]

    @staticmethod
    def check_product(pid, tno):

        sql = """
            SELECT *
            FROM record
            WHERE pid = %s AND tno = %s
        """

        return DB.fetchone(sql, (pid, tno))

    @staticmethod
    def get_price(pid):

        sql = """
            SELECT price
            FROM product
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))[0]

    @staticmethod
    def add_product(input_data):

        sql = """
            INSERT INTO record
            (pid, tno, amount, saleprice, total)
            VALUES (%s, %s, 1, %s, %s)
        """

        DB.execute_input(sql, (
            input_data['pid'],
            input_data['tno'],
            input_data['saleprice'],
            input_data['total']
        ))

    @staticmethod
    def get_record(tno):

        sql = """
            SELECT *
            FROM record
            WHERE tno = %s
        """

        return DB.fetchall(sql, (tno,))

    @staticmethod
    def get_amount(tno, pid):

        sql = """
            SELECT amount
            FROM record
            WHERE tno = %s AND pid = %s
        """

        return DB.fetchone(sql, (tno, pid))[0]

    @staticmethod
    def update_product(input_data):

        sql = """
            UPDATE record
            SET amount = %s,
                total = %s
            WHERE pid = %s AND tno = %s
        """

        DB.execute_input(sql, (
            input_data['amount'],
            input_data['total'],
            input_data['pid'],
            input_data['tno']
        ))

    @staticmethod
    def delete_check(pid):

        sql = """
            SELECT *
            FROM record
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))

    @staticmethod
    def get_total(tno):

        sql = """
            SELECT SUM(total)
            FROM record
            WHERE tno = %s
        """

        return DB.fetchone(sql, (tno,))[0]


# ==========================================
# 原始書店系統：訂單
# ==========================================

class Order_List:

    @staticmethod
    def add_order(input_data):

        sql = """
            INSERT INTO order_list
            (oid, mid, ordertime, price, tno)
            VALUES (
                DEFAULT,
                %s,
                TO_TIMESTAMP(%s, %s),
                %s,
                %s
            )
        """

        DB.execute_input(sql, (
            input_data['mid'],
            input_data['ordertime'],
            input_data['format'],
            input_data['total'],
            input_data['tno']
        ))

    @staticmethod
    def get_order():

        sql = """
            SELECT
                o.oid,
                m.name,
                o.price,
                o.ordertime
            FROM order_list o
            NATURAL JOIN member m
            ORDER BY o.ordertime DESC
        """

        return DB.fetchall(sql)

    @staticmethod
    def get_orderdetail():

        sql = """
            SELECT
                o.oid,
                p.pname,
                r.saleprice,
                r.amount
            FROM order_list o
            JOIN record r
                ON o.tno = r.tno
            JOIN product p
                ON r.pid = p.pid
        """

        return DB.fetchall(sql)


# ==========================================
# 原始書店系統：統計分析
# ==========================================

class Analysis:

    @staticmethod
    def month_price(i):

        sql = """
            SELECT
                EXTRACT(MONTH FROM ordertime),
                SUM(price)
            FROM order_list
            WHERE EXTRACT(MONTH FROM ordertime) = %s
            GROUP BY EXTRACT(MONTH FROM ordertime)
        """

        return DB.fetchall(sql, (i,))

    @staticmethod
    def month_count(i):

        sql = """
            SELECT
                EXTRACT(MONTH FROM ordertime),
                COUNT(oid)
            FROM order_list
            WHERE EXTRACT(MONTH FROM ordertime) = %s
            GROUP BY EXTRACT(MONTH FROM ordertime)
        """

        return DB.fetchall(sql, (i,))

    @staticmethod
    def category_sale():

        sql = """
            SELECT
                SUM(total),
                category
            FROM product, record
            WHERE product.pid = record.pid
            GROUP BY category
        """

        return DB.fetchall(sql)

    @staticmethod
    def member_sale():

        sql = """
            SELECT
                SUM(price),
                member.mid,
                member.name
            FROM order_list, member
            WHERE order_list.mid = member.mid
              AND member.identity = %s
            GROUP BY member.mid, member.name
            ORDER BY SUM(price) DESC
        """

        return DB.fetchall(sql, ('user',))

    @staticmethod
    def member_sale_count():

        sql = """
            SELECT
                COUNT(*),
                member.mid,
                member.name
            FROM order_list, member
            WHERE order_list.mid = member.mid
              AND member.identity = %s
            GROUP BY member.mid, member.name
            ORDER BY COUNT(*) DESC
        """

        return DB.fetchall(sql, ('user',))


# ==========================================
# 校園場館後台：共用交易與錯誤
# ==========================================


class RecordNotFound(Exception):
    """指定資料不存在或已刪除。"""


class RecordConflict(Exception):
    """資料狀態不允許操作，或使用了過期版本。"""


@contextmanager
def transaction():
    connection = DB.connect()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        DB.release(connection)


def fetch(sql, params=()):
    with transaction() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def lock_schedule(cursor):
    # 場地變更及預約審核使用同一交易鎖，避免同時核准重疊時段。
    cursor.execute('SELECT pg_advisory_xact_lock(9042026)')


class Reservation:
    STATUS = {'pending': '待審核', 'approved': '已核准', 'rejected': '已駁回', 'cancelled': '已取消'}

    @staticmethod
    def get(reservation_id):
        rows = fetch('''SELECT r.*, u.user_name, u.email FROM reservation r
            JOIN app_user u ON u.uid=r.applicant_uid
            WHERE r.id=%s AND r.deleted_at IS NULL''', (reservation_id,))
        if not rows:
            raise RecordNotFound()
        return rows[0]

    @staticmethod
    def users():
        return fetch('SELECT uid, user_name FROM app_user ORDER BY user_name, uid')

    @staticmethod
    def search(status='', query='', start=None, end=None, page=1):
        clauses, params = ['r.deleted_at IS NULL'], []
        if status:
            clauses.append('r.status=%s')
            params.append(status)
        if query:
            escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            clauses.append('(r.venue ILIKE %s OR u.user_name ILIKE %s OR r.applicant_uid ILIKE %s)')
            params.extend(['%' + escaped + '%'] * 3)
        if start:
            clauses.append('r.starts_at >= %s')
            params.append(start)
        if end:
            clauses.append('r.starts_at < %s')
            params.append(end + timedelta(days=1))
        where = ' AND '.join(clauses)
        total = fetch('SELECT count(*) AS n FROM reservation r JOIN app_user u ON u.uid=r.applicant_uid WHERE ' + where, params)[0]['n']
        pages = max(1, (total + 19) // 20)
        page = min(page, pages)
        rows = fetch('''SELECT r.*, u.user_name FROM reservation r
            JOIN app_user u ON u.uid=r.applicant_uid WHERE ''' + where +
            ' ORDER BY r.starts_at DESC, r.id DESC LIMIT 20 OFFSET %s', params + [(page-1)*20])
        return rows, total, page, pages

    @staticmethod
    def history(reservation_id):
        return fetch('''SELECT a.*, u.user_name FROM reservation_audit a
            JOIN app_user u ON u.uid=a.actor_uid WHERE reservation_id=%s
            ORDER BY a.occurred_at DESC, a.id DESC''', (reservation_id,))

    @staticmethod
    def audit(cursor, reservation_id, actor_uid, action, note=''):
        cursor.execute('''INSERT INTO reservation_audit(reservation_id,actor_uid,action,note)
            VALUES(%s,%s,%s,%s)''', (reservation_id,actor_uid,action,note))

    @staticmethod
    def locked(cursor, reservation_id, version):
        lock_schedule(cursor)
        cursor.execute('SELECT * FROM reservation WHERE id=%s AND deleted_at IS NULL FOR UPDATE', (reservation_id,))
        row = cursor.fetchone()
        if not row:
            raise RecordNotFound()
        if str(version) != str(row['version']):
            raise RecordConflict('資料已被其他管理者更新，請重新載入再操作。')
        return row

    @staticmethod
    def require_editable(row):
        if row['status'] != 'pending' or row['reviewed_at']:
            raise RecordConflict('僅未審核的待審核預約可以修改；已審核預約請建立新申請。')

    @staticmethod
    def check_overlap(cursor, values, reservation_id=0):
        cursor.execute('''SELECT id FROM reservation WHERE deleted_at IS NULL
            AND status='approved' AND venue_id=%s
            AND starts_at < %s AND ends_at > %s AND id != %s LIMIT 1''',
            (values['venue_id'],values['ends_at'],values['starts_at'],reservation_id))
        if cursor.fetchone():
            raise ValueError('此場地時段已有核准預約，請調整場地或時間。')

    @staticmethod
    def save(values, actor_uid, reservation_id=None, version=None):
        with transaction() as cursor:
            if reservation_id is not None:
                Reservation.require_editable(Reservation.locked(cursor,reservation_id,version))
            else:
                lock_schedule(cursor)
            cursor.execute('SELECT uid FROM app_user WHERE uid=%s', (values['applicant_uid'],))
            if not cursor.fetchone():
                raise ValueError('申請人帳號不存在。')
            venue = Venue.check_available(cursor,values['venue_id'],values['attendees'])
            Reservation.check_overlap(cursor,values,reservation_id or 0)
            params = (values['applicant_uid'],venue['venue_name'],values['starts_at'],
                      values['ends_at'],values['purpose'],values['attendees'],values['venue_id'])
            if reservation_id is None:
                cursor.execute('''INSERT INTO reservation
                    (applicant_uid,venue,starts_at,ends_at,purpose,attendees,venue_id,created_by)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''', params+(actor_uid,))
                reservation_id = cursor.fetchone()['id']
                Reservation.audit(cursor,reservation_id,actor_uid,'create','建立預約，待審核')
            else:
                cursor.execute('''UPDATE reservation SET applicant_uid=%s,venue=%s,starts_at=%s,
                    ends_at=%s,purpose=%s,attendees=%s,venue_id=%s,
                    updated_at=now(),version=version+1 WHERE id=%s''',params+(reservation_id,))
                Reservation.audit(cursor,reservation_id,actor_uid,'edit','修改未審核預約')
        return reservation_id

    @staticmethod
    def review(reservation_id, version, decision, note, actor_uid):
        with transaction() as cursor:
            row = Reservation.locked(cursor,reservation_id,version)
            Reservation.require_editable(row)
            if decision == 'approved':
                Venue.check_available(cursor,row['venue_id'],row['attendees'])
                Reservation.check_overlap(cursor,row,reservation_id)
            cursor.execute('''UPDATE reservation SET status=%s,review_note=%s,reviewed_by=%s,
                reviewed_at=now(),updated_at=now(),version=version+1 WHERE id=%s''',
                (decision,note,actor_uid,reservation_id))
            Reservation.audit(cursor,reservation_id,actor_uid,decision,note)

    @staticmethod
    def remove(reservation_id, version, actor_uid, cancel=False):
        with transaction() as cursor:
            row = Reservation.locked(cursor,reservation_id,version)
            if cancel and row['status'] not in ('pending','approved'):
                raise RecordConflict('只有待審核或已核准預約可以取消。')
            cursor.execute('SELECT rid FROM usage_record WHERE rid=%s',(reservation_id,))
            if cursor.fetchone():
                raise RecordConflict('已有實際使用紀錄，請先處理使用紀錄再取消或刪除預約。')
            if cancel:
                cursor.execute("UPDATE reservation SET status='cancelled',version=version+1,updated_at=now() WHERE id=%s",(reservation_id,))
                action,note = 'cancel','取消預約；保留原審核資訊'
            else:
                cursor.execute('UPDATE reservation SET deleted_at=now(),updated_at=now(),version=version+1 WHERE id=%s',(reservation_id,))
                action,note = 'delete','刪除預約；保留稽核紀錄'
            Reservation.audit(cursor,reservation_id,actor_uid,action,note)


class Venue:
    @staticmethod
    def get(vid, include_deleted=False):
        rows = fetch('SELECT * FROM venue WHERE vid=%s' + ('' if include_deleted else ' AND deleted_at IS NULL'),(vid,))
        if not rows:
            raise RecordNotFound()
        return rows[0]

    @staticmethod
    def equipment(vid):
        return fetch('SELECT * FROM venue_equipment WHERE vid=%s ORDER BY equipment_name',(vid,))

    @staticmethod
    def get_all(open_only=False):
        return fetch('''SELECT v.*,(SELECT count(*) FROM venue_equipment e WHERE e.vid=v.vid) AS equipment_count
            FROM venue v WHERE v.deleted_at IS NULL''' + (" AND v.status='open'" if open_only else '') + ' ORDER BY v.venue_name')

    @staticmethod
    def check_available(cursor,vid,attendees):
        cursor.execute('SELECT * FROM venue WHERE vid=%s AND deleted_at IS NULL FOR UPDATE',(vid,))
        venue = cursor.fetchone()
        if not venue or venue['status'] != 'open':
            raise ValueError('此場地未開放預約。')
        if attendees > venue['capacity']:
            raise ValueError('預計使用人數超過場地容納上限。')
        return venue

    @staticmethod
    def save(values,items,vid=None):
        name,kind,capacity,status,description = (values[key] for key in
            ('venue_name','venue_type','capacity','status','description'))
        with transaction() as cursor:
            lock_schedule(cursor)
            cursor.execute('SELECT vid FROM venue WHERE lower(trim(venue_name))=lower(trim(%s)) AND deleted_at IS NULL AND vid != %s',(name,vid or 0))
            if cursor.fetchone():
                raise ValueError('場地名稱已存在。')
            if vid:
                cursor.execute('SELECT vid FROM venue WHERE vid=%s AND deleted_at IS NULL FOR UPDATE',(vid,))
                if not cursor.fetchone():
                    raise RecordNotFound()
                cursor.execute('''SELECT id FROM reservation WHERE venue_id=%s AND deleted_at IS NULL
                    AND status='approved' AND ends_at > %s AND (attendees > %s OR %s != 'open') LIMIT 1''',
                    (vid,datetime.now(ZoneInfo('Asia/Taipei')).replace(tzinfo=None),capacity,status))
                if cursor.fetchone():
                    raise ValueError('此變更會影響尚未結束的核准預約，請先處理相關預約。')
                cursor.execute('UPDATE venue SET venue_name=%s,venue_type=%s,capacity=%s,status=%s,description=%s WHERE vid=%s',(name,kind,capacity,status,description,vid))
                cursor.execute('UPDATE reservation SET venue=%s WHERE venue_id=%s',(name,vid))
                cursor.execute('DELETE FROM venue_equipment WHERE vid=%s',(vid,))
            else:
                cursor.execute('INSERT INTO venue(venue_name,venue_type,capacity,status,description) VALUES(%s,%s,%s,%s,%s) RETURNING vid',(name,kind,capacity,status,description))
                vid = cursor.fetchone()['vid']
            for item in items:
                cursor.execute('INSERT INTO venue_equipment(vid,equipment_name,status,quantity) VALUES(%s,%s,%s,%s)',(vid,)+item)
        return vid

    @staticmethod
    def delete(vid):
        with transaction() as cursor:
            lock_schedule(cursor)
            cursor.execute('SELECT vid FROM venue WHERE vid=%s AND deleted_at IS NULL FOR UPDATE',(vid,))
            if not cursor.fetchone():
                raise RecordNotFound()
            cursor.execute('''SELECT id FROM reservation WHERE venue_id=%s AND deleted_at IS NULL
                AND status IN ('pending','approved') AND ends_at > %s LIMIT 1''',
                (vid,datetime.now(ZoneInfo('Asia/Taipei')).replace(tzinfo=None)))
            if cursor.fetchone():
                raise RecordConflict('場地仍有待審核或核准預約，請先處理後再刪除。')
            cursor.execute("UPDATE venue SET deleted_at=now(),status='closed' WHERE vid=%s",(vid,))


class UsageRecord:
    @staticmethod
    def get(reservation_id):
        rows = fetch('SELECT * FROM usage_record WHERE rid=%s',(reservation_id,))
        return rows[0] if rows else None

    @staticmethod
    def save(reservation_id,version,start,end,comment,actor_uid):
        with transaction() as cursor:
            row = Reservation.locked(cursor,reservation_id,version)
            if row['status'] != 'approved':
                raise RecordConflict('只有已核准預約可以建立使用紀錄。')
            cursor.execute('''INSERT INTO usage_record(rid,start_time,end_time,comment) VALUES(%s,%s,%s,%s)
                ON CONFLICT(rid) DO UPDATE SET start_time=excluded.start_time,
                end_time=excluded.end_time,comment=excluded.comment''',(reservation_id,start,end,comment))
            cursor.execute('UPDATE reservation SET version=version+1,updated_at=now() WHERE id=%s',(reservation_id,))
            Reservation.audit(cursor,reservation_id,actor_uid,'usage','儲存實際使用時間與回饋')

    @staticmethod
    def delete(reservation_id,version,actor_uid):
        with transaction() as cursor:
            Reservation.locked(cursor,reservation_id,version)
            cursor.execute('DELETE FROM usage_record WHERE rid=%s RETURNING rid',(reservation_id,))
            if not cursor.fetchone():
                raise RecordNotFound()
            cursor.execute('UPDATE reservation SET version=version+1,updated_at=now() WHERE id=%s',(reservation_id,))
            Reservation.audit(cursor,reservation_id,actor_uid,'usage_delete','刪除實際使用紀錄')


class ReservationAnalysis:
    @staticmethod
    def dashboard(today):
        summary = fetch('''SELECT count(*) AS total,
            count(*) FILTER (WHERE status='pending') AS pending,
            count(*) FILTER (WHERE status='approved') AS approved,
            count(*) FILTER (WHERE status='rejected') AS rejected,
            count(*) FILTER (WHERE status='cancelled') AS cancelled,
            count(*) FILTER (WHERE status='approved' AND starts_at < %s AND ends_at > %s) AS today,
            coalesce(sum(extract(epoch FROM (ends_at-starts_at))/3600)
                FILTER (WHERE status='approved'),0) AS hours
            FROM reservation WHERE deleted_at IS NULL''',(today+timedelta(days=1),today))[0]
        monthly = fetch('''SELECT to_char(m.month,'YYYY-MM') AS month,count(r.id) AS total,
            count(r.id) FILTER (WHERE r.status='approved') AS approved
            FROM generate_series(date_trunc('month',%s::date)-interval '5 months',
                date_trunc('month',%s::date),interval '1 month') AS m(month)
            LEFT JOIN reservation r ON r.starts_at >= m.month
                AND r.starts_at < m.month+interval '1 month' AND r.deleted_at IS NULL
            GROUP BY m.month ORDER BY m.month''',(today,today))
        venues = fetch('''SELECT venue,count(*) AS total FROM reservation WHERE deleted_at IS NULL
            GROUP BY venue ORDER BY total DESC,venue LIMIT 6''')
        usage_stats = fetch('''SELECT count(*) AS total,
            count(*) FILTER (WHERE ur.end_time IS NULL) AS active,
            count(*) FILTER (WHERE ur.end_time IS NOT NULL) AS completed,
            count(*) FILTER (WHERE trim(ur.comment) != '') AS feedback
            FROM usage_record ur JOIN reservation r ON r.id=ur.rid WHERE r.deleted_at IS NULL''')[0]
        pending = fetch('''SELECT r.*,u.user_name FROM reservation r JOIN app_user u ON u.uid=r.applicant_uid
            WHERE r.deleted_at IS NULL AND r.status='pending' ORDER BY r.created_at,r.id LIMIT 5''')
        return dict(summary=summary,monthly=monthly,venues=venues,pending=pending,usage_stats=usage_stats,
                    month_max=max([row['total'] for row in monthly]+[1]),
                    venue_max=max([row['total'] for row in venues]+[1]))


class CampusAdmin:
    @staticmethod
    def initialize(migrations):
        with transaction() as cursor:
            for migration in migrations:
                cursor.execute(migration.read_text(encoding='utf-8'))

    @staticmethod
    def create_manager(uid,name,email,password_hash):
        with transaction() as cursor:
            cursor.execute('SELECT uid FROM app_user WHERE uid=%s OR email=%s',(uid,email))
            if cursor.fetchone():
                raise ValueError('編號或電子郵件已存在，未變更任何帳號。')
            cursor.execute('''INSERT INTO app_user(uid,user_name,password_hash,identity,email,did)
                VALUES(%s,%s,%s,'manager',%s,'GENERAL')''',(uid,name,password_hash,email))
