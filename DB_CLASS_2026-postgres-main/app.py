import os
from flask import Flask, render_template,redirect, url_for
from api.api import api, login_manager


app = Flask(__name__)

# Flask Session 金鑰
app.secret_key = os.environ.get(
    'FLASK_SECRET_KEY',
    'development-only-change-this-key'
)

# 註冊使用者功能
app.register_blueprint(api, url_prefix='/')

# 初始化 Flask-Login
login_manager.init_app(app)


# 首頁
@app.route('/')
def index():
    return redirect(url_for('api.login'))


if __name__ == '__main__':
    app.run(debug=True)
