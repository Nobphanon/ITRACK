import os
from flask import Flask
from flask_login import LoginManager
from models import init_db, get_db, User
# ✅ 1. นำเข้า mail จากไฟล์ extensions
from extensions import mail 

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_PERMANENT'] = False

# -------------------------------------------------------------------------
# ✅ 2. เพิ่มการตั้งค่าอีเมล (Gmail Config)
# -------------------------------------------------------------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

# อีเมลผู้ส่ง (เปิดเผยได้ ไม่เป็นไร)
app.config['MAIL_USERNAME'] = 'kissmemore248@gmail.com' 


app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 

app.config['MAIL_DEFAULT_SENDER'] = ('ITRACK Alert', app.config['MAIL_USERNAME'])

# ✅ 3. เริ่มการทำงานของระบบส่งเมล
mail.init_app(app) 
# -------------------------------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if u:
        return User(u['id'], u['username'], u['email'], u['role'])
    return None

from auth.routes import auth_bp
from Research.routes import research_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(research_bp)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)