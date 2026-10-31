"""場館後台控制器：處理權限、表單、導頁；SQL 集中於 api/sql.py。"""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from api.api import manager_required
from api.sql import Reservation, Venue, UsageRecord

manager = Blueprint('manager', __name__, template_folder='../templates', url_prefix='/admin')


@manager.app_context_processor
def labels():
    return {'status_labels': Reservation.STATUS, 'taipei': ZoneInfo('Asia/Taipei')}


def validate_form():
    values = {key: request.form.get(key, '').strip() for key in
              ('applicant_uid', 'venue_id', 'starts_at', 'ends_at', 'purpose', 'attendees')}
    if not values['applicant_uid'] or not values['venue_id'] or not values['purpose']:
        raise ValueError('請填寫申請人、場地與用途。')
    if len(values['purpose']) > 1000:
        raise ValueError('用途最多 1000 字。')
    try:
        values['starts_at'] = datetime.strptime(values['starts_at'], '%Y-%m-%dT%H:%M')
        values['ends_at'] = datetime.strptime(values['ends_at'], '%Y-%m-%dT%H:%M')
        values['attendees'] = int(values['attendees'])
        values['venue_id'] = int(values['venue_id'])
    except ValueError:
        raise ValueError('請輸入有效的起訖時間與人數。')
    if values['ends_at'] <= values['starts_at']:
        raise ValueError('結束時間必須晚於開始時間。')
    if not 1 <= values['venue_id'] <= 9223372036854775807:
        raise ValueError('請選擇有效場地。')
    if not 1 <= values['attendees'] <= 100000:
        raise ValueError('人數必須介於 1 到 100000。')
    return values

@manager.route('/reservations')
@manager_required
def reservation_list():
    status = request.args.get('status', '')
    query = request.args.get('q', '').strip()[:128]
    start, end = request.args.get('from', ''), request.args.get('to', '')
    if status and status not in Reservation.STATUS:
        abort(400, '不正確的預約狀態')
    try:
        start_date = date.fromisoformat(start) if start else None
        end_date = date.fromisoformat(end) if end else None
        if start_date and end_date and start_date > end_date:
            raise ValueError()
        page = max(1, int(request.args.get('page', 1)))
        # 驗證上界，避免資料查詢的日期加一天發生溢位。
        if end_date == date.max:
            raise ValueError()
    except (ValueError, OverflowError):
        abort(400, '日期或頁碼不正確')
    rows, total, page, pages = Reservation.search(status,query,start_date,end_date,page)
    links = {p: url_for('manager.reservation_list',status=status,q=query,
                       **{'from':start,'to':end,'page':p}) for p in (page-1,page+1)}
    return render_template('reservationManager.html',rows=rows,total=total,page=page,
                           pages=pages,links=links,filters={'status':status,'q':query,'from':start,'to':end})


@manager.route('/reservations/new', methods=['GET','POST'])
@manager.route('/reservations/<int:reservation_id>/edit', methods=['GET','POST'])
@manager_required
def reservation_form(reservation_id=None):
    record = Reservation.get(reservation_id) if reservation_id is not None else None
    if record:
        Reservation.require_editable(record)
    error = None
    if request.method == 'POST':
        try:
            reservation_id = Reservation.save(validate_form(),current_user.id,reservation_id,request.form.get('version'))
            flash('預約已儲存，等待審核。','success')
            return redirect(url_for('manager.reservation_detail',reservation_id=reservation_id))
        except ValueError as exc:
            error = str(exc)
    form = request.form if request.method == 'POST' else (record or {})
    return render_template('reservationForm.html',record=record,form=form,
                           users=Reservation.users(),venues=Venue.get_all(open_only=True),error=error), (400 if error else 200)


@manager.route('/reservations/<int:reservation_id>')
@manager_required
def reservation_detail(reservation_id):
    record = Reservation.get(reservation_id)
    return render_template('reservationDetail.html',record=record,history=Reservation.history(reservation_id),
                           usage=UsageRecord.get(reservation_id),
                           venue=Venue.get(record['venue_id'],include_deleted=True),
                           equipment=Venue.equipment(record['venue_id']))


@manager.route('/reservations/<int:reservation_id>/review', methods=['POST'])
@manager_required
def reservation_review(reservation_id):
    decision = request.form.get('decision')
    note = request.form.get('review_note','').strip()
    if decision not in ('approved','rejected') or len(note) > 1000:
        abort(400,'審核結果或意見不正確')
    if decision == 'rejected' and not note:
        flash('駁回時請填寫原因。','error')
    else:
        try:
            Reservation.review(reservation_id,request.form.get('version'),decision,note,current_user.id)
            flash('審核完成。','success')
        except ValueError as exc:
            flash(str(exc),'error')
    return redirect(url_for('manager.reservation_detail',reservation_id=reservation_id))


@manager.route('/reservations/<int:reservation_id>/delete', methods=['POST'])
@manager_required
def reservation_delete(reservation_id):
    Reservation.remove(reservation_id,request.form.get('version'),current_user.id)
    flash('預約已刪除。','success')
    return redirect(url_for('manager.reservation_list'))


@manager.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
@manager_required
def reservation_cancel(reservation_id):
    Reservation.remove(reservation_id,request.form.get('version'),current_user.id,cancel=True)
    flash('預約已取消。','success')
    return redirect(url_for('manager.reservation_detail',reservation_id=reservation_id))


@manager.route('/venues')
@manager_required
def venue_list():
    return render_template('venueManager.html',rows=Venue.get_all())


@manager.route('/venues/<int:vid>')
@manager_required
def venue_detail(vid):
    return render_template('venueDetail.html',venue=Venue.get(vid),equipment=Venue.equipment(vid))


def validate_venue_form():
    values = {key:request.form.get(key,'').strip() for key in
              ('venue_name','venue_type','status','description')}
    try:
        values['capacity'] = int(request.form.get('capacity','0'))
    except ValueError:
        raise ValueError('容納人數必須為整數。')
    if not values['venue_name'] or len(values['venue_name']) > 128 or not values['venue_type'] or len(values['venue_type']) > 80:
        raise ValueError('請填寫有效的場地名稱（最多128字）及類型（最多80字）。')
    if not 1 <= values['capacity'] <= 100000 or values['status'] not in ('open','closed','maintenance') or len(values['description']) > 2000:
        raise ValueError('請確認容納人數、狀態及說明（最多2000字）。')
    items, names = [], set()
    for line in request.form.get('equipment','').splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split('|')]
        if len(parts) != 3 or not parts[0] or len(parts[0]) > 128 or not parts[1] or len(parts[1]) > 80:
            raise ValueError('器材每行請填寫：器材名稱 | 狀態 | 數量。')
        try:
            quantity = int(parts[2])
        except ValueError:
            raise ValueError('器材數量必須為整數。')
        if not 0 <= quantity <= 100000 or parts[0] in names:
            raise ValueError('器材名稱不可重複，數量必須為 0–100000。')
        names.add(parts[0])
        items.append((parts[0],parts[1],quantity))
    return values,items


@manager.route('/venues/new', methods=['GET','POST'])
@manager.route('/venues/<int:vid>/edit', methods=['GET','POST'])
@manager_required
def venue_form(vid=None):
    venue = Venue.get(vid) if vid else None
    error = None
    if request.method == 'POST':
        try:
            values, items = validate_venue_form()
            vid = Venue.save(values,items,vid)
            flash('場地與器材已儲存。','success')
            return redirect(url_for('manager.venue_detail',vid=vid))
        except ValueError as exc:
            error = str(exc)
    equipment = Venue.equipment(vid) if vid else []
    equipment_text = '\n'.join(f"{e['equipment_name']} | {e['status']} | {e['quantity']}" for e in equipment)
    return render_template('venueForm.html',venue=venue,
                           form=request.form if request.method=='POST' else (venue or {}),
                           equipment_text=equipment_text,error=error), (400 if error else 200)


@manager.route('/venues/<int:vid>/delete', methods=['POST'])
@manager_required
def venue_delete(vid):
    Venue.delete(vid)
    flash('場地已刪除，歷史預約資料仍保留。','success')
    return redirect(url_for('manager.venue_list'))


@manager.route('/reservations/<int:reservation_id>/usage', methods=['POST'])
@manager_required
def usage_save(reservation_id):
    try:
        start = datetime.strptime(request.form.get('start_time',''),'%Y-%m-%dT%H:%M')
        end_text = request.form.get('end_time','')
        end = datetime.strptime(end_text,'%Y-%m-%dT%H:%M') if end_text else None
        comment = request.form.get('comment','').strip()
        if end and end <= start:
            raise ValueError('實際離開時間必須晚於開始時間。')
        if len(comment) > 2000:
            raise ValueError('使用回饋最多 2000 字。')
        UsageRecord.save(reservation_id,request.form.get('version'),start,end,comment,current_user.id)
        flash('實際使用紀錄已儲存。','success')
    except ValueError as exc:
        flash(str(exc) if 'does not match format' not in str(exc) else '請填寫有效的實際使用時間。','error')
    return redirect(url_for('manager.reservation_detail',reservation_id=reservation_id))


@manager.route('/reservations/<int:reservation_id>/usage/delete', methods=['POST'])
@manager_required
def usage_delete(reservation_id):
    UsageRecord.delete(reservation_id,request.form.get('version'),current_user.id)
    flash('使用紀錄已刪除。','success')
    return redirect(url_for('manager.reservation_detail',reservation_id=reservation_id))
