
from flask import (
    render_template, Blueprint, redirect,
    request, url_for, flash, abort
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from psycopg2.errors import UniqueViolation

from api.sql import AppUser, Department


# ==========================================
# Blueprint 與登入管理
# ==========================================

api = Blueprint(
    'api',
    __name__,
    template_folder='./templates'
)

login_manager = LoginManager()
login_manager.login_view = 'api.login'
login_manager.login_message = "請先登入"


# ==========================================
# 使用者物件
# ==========================================

class User(UserMixin):
    pass


# ==========================================
# 讀取已登入使用者
# ==========================================

@login_manager.user_loader
def user_loader(userid):

    data = AppUser.get_role(userid)

    if data is None:
        return None

    user = User()
    user.id = str(userid)
    user.role = data[0]
    user.name = data[1]

    return user


# ==========================================
# 登入
# ==========================================

@api.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        # 使用學號／員工編號登入
        uid = request.form.get(
            'uid', ''
        ).strip().upper()

        password = request.form.get(
            'password', ''
        )

        # 確認帳號與密碼都有填寫
        if not uid or not password:
            flash('請輸入學號／員工編號及密碼', 'error')
            return redirect(
                url_for('api.login')
            )

        # 依照 UID 查詢使用者
        data = AppUser.get_user(uid)

        if data is None:
            flash('學號／員工編號或密碼錯誤', 'error')
            return redirect(
                url_for('api.login')
            )

        user_uid = data[0]
        username = data[1]
        password_hash = data[2]
        identity = data[3]

        # 驗證密碼
        if not check_password_hash(
            password_hash, password
        ):
            flash('學號／員工編號或密碼錯誤', 'error')
            return redirect(
                url_for('api.login')
            )

        # 建立登入使用者
        user = User()
        user.id = str(user_uid)
        user.name = username
        user.role = identity

        login_user(user)

        # 依照身分導向不同首頁
        if identity == 'manager':
            return redirect(
                url_for('api.admin_home')
            )

        return redirect(
            url_for('api.user_home')
        )

    return render_template('login.html')


# ==========================================
# 註冊
# ==========================================

@api.route('/register', methods=['GET', 'POST'])
def register():

    # 取得所有系所
    departments = Department.get_all()

    if request.method == 'POST':

        # 學號／員工編號
        uid = request.form.get(
            'uid', ''
        ).strip().upper()

        # 姓名
        username = request.form.get(
            'username', ''
        ).strip()

        # 電子郵件
        email = request.form.get(
            'email', ''
        ).strip().lower()

        # 密碼
        password = request.form.get(
            'password', ''
        )

        # 聯絡電話
        phone = request.form.get(
            'phone', ''
        ).strip()

        # 所屬單位代碼（VARCHAR）
        did = request.form.get(
            'did', ''
        ).strip()

        # ==================================
        # 1. 基本資料驗證
        # ==================================

        if (
            not uid
            or not username
            or not email
            or len(password) < 8
        ):
            flash(
                '請填寫完整資料，密碼至少需要 8 個字元',
                'error'
            )
            return redirect(
                url_for('api.register')
            )

        # UID 長度限制
        if len(uid) > 20:
            flash(
                '學號／員工編號不可超過 20 個字元',
                'error'
            )
            return redirect(
                url_for('api.register')
            )

        # ==================================
        # 2. 確認所屬單位存在
        # ==================================

        valid_departments = [
            str(department[0])
            for department in departments
        ]

        if did not in valid_departments:
            flash('請選擇所屬單位', 'error')
            return redirect(
                url_for('api.register')
            )

        # ==================================
        # 3. 檢查 UID 是否重複
        # ==================================

        if AppUser.get_user(uid) is not None:
            flash(
                '此學號／員工編號已被註冊',
                'error'
            )
            return redirect(
                url_for('api.register')
            )

        # ==================================
        # 4. 檢查 Email 是否重複
        # ==================================

        if AppUser.get_user_by_email(email) is not None:
            flash(
                '此電子郵件已被註冊過',
                'error'
            )
            return redirect(
                url_for('api.register')
            )

        # ==================================
        # 5. 準備新增使用者資料
        # ==================================

        input_data = {
            'uid': uid,
            'user_name': username,
            'email': email,
            'password_hash': generate_password_hash(
                password
            ),
            'phone': phone or None,
            'did': did
        }

        # ==================================
        # 6. 寫入 PostgreSQL
        # ==================================

        try:
            AppUser.create_user(input_data)

        except UniqueViolation:
            flash(
                '學號／員工編號或電子郵件已被註冊',
                'error'
            )
            return redirect(
                url_for('api.register')
            )

        # 註冊成功
        flash('註冊成功，請登入', 'success')

        return redirect(
            url_for('api.login')
        )

    return render_template(
        'register.html',
        departments=departments
    )


# ==========================================
# 一般使用者首頁
# ==========================================

@api.route('/user/home')
@login_required
def user_home():

    # 只有學生與教師可以進入
    if current_user.role not in (
        'student', 'teacher'
    ):
        abort(403)

    return render_template(
        'user_homepage.html'
    )


# ==========================================
# 管理員首頁
# ==========================================

@api.route('/admin/home')
@login_required
def admin_home():

    # 只有 manager 可以進入
    if current_user.role != 'manager':
        abort(403)

    return render_template(
        'manager_homepage.html'
    )


# ==========================================
# 登出
# ==========================================

@api.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(
        url_for('index')
    )
