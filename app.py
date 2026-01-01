import os
from datetime import datetime
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
# 📧 Email Configuration (HARDENED)
# =========================================================
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_TIMEOUT'] = 30

# ---- CRITICAL FIX: Never allow None sender ----
if not app.config['MAIL_USERNAME']:
    raise RuntimeError("MAIL_USERNAME is missing")

app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

print("📨 Mail config loaded:")
print("  Server:", app.config['MAIL_SERVER'])
print("  User:", app.config['MAIL_USERNAME'])

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
# 🚀 Blueprints
# =========================================================
from auth.routes import auth_bp
from Research.routes import research_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(research_bp)

# =========================================================
# 🧱 Database Initialization
# =========================================================
with app.app_context():
    init_db()

# =========================================================
# 🧪 Mail Health Check Route
# =========================================================
from flask_mail import Message

@app.route('/_mail_test')
def mail_test():
    msg = Message(
        subject="ITRACK MAIL SYSTEM OK",
        recipients=[app.config['MAIL_USERNAME']],
        body="If you see this email, your system is working perfectly."
    )
    with app.app_context():
        mail.send(msg)
    return "Mail sent successfully"

# =========================================================
# ⏰ Scheduler Endpoint
# =========================================================
from notifications.scheduler import notify_deadlines

@app.route('/cron/check-deadlines', methods=['GET', 'POST'])
def check_deadlines_endpoint():
    try:
        count = notify_deadlines()
        return {
            'success': True,
            'message': f'Sent {count} notification(s)',
            'timestamp': datetime.now().isoformat()
        }, 200
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

# =========================================================
# 🚀 Run
# =========================================================
if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=True
    )
