import os
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from models import init_db, get_db, User
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SESSION_PERMANENT'] = False

# =========================================================
# 📧 SendGrid Configuration
# =========================================================
app.config['SENDGRID_API_KEY'] = os.getenv("SENDGRID_API_KEY")
app.config['MAIL_SENDER'] = os.getenv("MAIL_SENDER")

if not app.config['SENDGRID_API_KEY'] or not app.config['MAIL_SENDER']:
    raise RuntimeError("SENDGRID_API_KEY or MAIL_SENDER is missing")

print("📨 SendGrid ready:")
print("  Sender:", app.config['MAIL_SENDER'])

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
