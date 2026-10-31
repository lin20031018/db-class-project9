import os
import secrets
from flask import Flask, render_template,redirect, url_for
from api.api import api, login_manager, register_commands, init_csrf
from backstage.views.manager import manager
from backstage.views.analysis import analysis


app = Flask(__name__)

# Flask Session 金鑰
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)

# 註冊使用者功能
app.register_blueprint(api, url_prefix='/')
app.register_blueprint(manager)
app.register_blueprint(analysis)
register_commands(app)
init_csrf(app)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')

# 初始化 Flask-Login
login_manager.init_app(app)


# 首頁
@app.route('/')
def index():
    return redirect(url_for('api.login'))


if __name__ == '__main__':
    app.run(debug=True)
