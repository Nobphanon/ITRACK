import os
from datetime import datetime  # ✅ เพิ่มบรรทัดนี้แล้ว (แก้ Error)
from flask import Flask
from flask_login import LoginManager
from models import init_db, get_db, User
from extensions import mail
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SESSION_PERMANENT'] = False

# =========================================================
# 📧 Email Configuration
# =========================================================
# ✅ เพิ่มการตรวจสอบค่า Environment Variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', ('ITRACK Alert', app.config['MAIL_USERNAME']))

# Debug: เช็คว่าโหลดค่ามาได้จริงไหม
if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
    print("⚠️ WARNING: MAIL_USERNAME or MAIL_PASSWORD not set!")
else:
    print(f"✅ Mail configured for: {app.config['MAIL_USERNAME']}")

mail.init_app(app)

# =========================================================
# 🔐 Login Manager
# =========================================================
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

# =========================================================
# 🚀 Blueprints & Routes
# =========================================================
from auth.routes import auth_bp
from Research.routes import research_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(research_bp)

# ✅ Import Scheduler (ต้องมีไฟล์ notifications/scheduler.py ด้วยนะ)
from notifications.scheduler import notify_deadlines

# Route สำหรับ Cron Jobs หรือยิงทดสอบ
@app.route('/cron/check-deadlines', methods=['GET', 'POST'])
def check_deadlines_endpoint():
    """
    Endpoint สำหรับตรวจสอบ deadlines
    สามารถเรียกผ่าน Render Cron Jobs หรือ manual trigger
    """
    try:
        count = notify_deadlines()
        return {
            'success': True,
            'message': f'Sent {count} notification(s)',
            'timestamp': datetime.now().isoformat() # ✅ ใช้งานได้แล้ว
        }, 200
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

if __name__ == "__main__":
    init_db()
    # ✅ เปลี่ยน debug=False สำหรับ production, True สำหรับ dev ในเครื่อง
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)