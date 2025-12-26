import os
from flask import Flask
from flask_login import LoginManager
from models import init_db, get_db, User
from extensions import mail 

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_PERMANENT'] = False

# -------------------------------------------------------------------------
# ✅ ตั้งค่าอีเมล
# -------------------------------------------------------------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kissmemore248@gmail.com' 
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = ('ITRACK Alert', app.config['MAIL_USERNAME'])

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

# ✅✅✅ จุดสำคัญที่แก้ไข (ห้ามเอาไว้ข้างล่างสุด!)
# สั่งให้สร้าง Database ทันทีที่ Render เริ่มรันโปรแกรม
with app.app_context():
    init_db()

# ส่วนนี้ Render จะไม่เข้ามาอ่าน แต่เอาไว้เผื่อรันในเครื่องตัวเอง
if __name__ == "__main__":
    app.run(debug=True)