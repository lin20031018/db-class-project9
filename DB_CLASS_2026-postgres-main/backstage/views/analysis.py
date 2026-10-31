"""預約分析控制器：統計查詢集中於 api.sql.ReservationAnalysis。"""
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template
from api.api import manager_required
from api.sql import ReservationAnalysis

analysis = Blueprint('analysis', __name__, template_folder='../templates', url_prefix='/admin')


@analysis.route('/dashboard')
@manager_required
def dashboard():
    today = datetime.now(ZoneInfo('Asia/Taipei')).date()
    return render_template('dashboard.html', **ReservationAnalysis.dashboard(today))
