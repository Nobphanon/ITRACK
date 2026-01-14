import os
import logging
from datetime import datetime
from flask import Flask, request, render_template
from flask_login import LoginManager
from dotenv import load_dotenv

from models import init_db, get_db, close_db, User
from auth.routes import auth_bp
from research.routes import research_bp
from notifications.scheduler import notify_deadlines
from extensions import csrf, limiter

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SESSION_PERMANENT'] = False

# Security: Maximum file upload size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# SendGrid Configuration
app.config['SENDGRID_API_KEY'] = os.getenv("SENDGRID_API_KEY")
app.config['MAIL_SENDER'] = os.getenv("MAIL_SENDER")

# Cron API Key for scheduled tasks
app.config['CRON_API_KEY'] = os.getenv("CRON_API_KEY", "")

if not app.config['SENDGRID_API_KEY'] or not app.config['MAIL_SENDER']:
    logger.warning("⚠️ SendGrid environment variables not configured")
else:
    logger.info(f"📨 SendGrid ready. Sender: {app.config['MAIL_SENDER']}")

# Initialize Extensions
csrf.init_app(app)
limiter.init_app(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "กรุณาเข้าสู่ระบบก่อนใช้งาน"
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if u:
        return User(u['id'], u['username'], u['email'], u['role'])
    return None

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(research_bp)

# Admin Blueprint (Admin only)
from admin.routes import admin_bp
app.register_blueprint(admin_bp)

# Researcher Blueprint  
from researcher.routes import researcher_bp
app.register_blueprint(researcher_bp)

# Database Initialization
with app.app_context():
    init_db()

@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db(exception)

# ---------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal Server Error: {e}")
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def file_too_large(e):
    return render_template('errors/413.html'), 413

# ---------------------------------------------------------
# Cron Endpoint (Protected by API Key)
# ---------------------------------------------------------

@app.route('/cron/check-deadlines', methods=['GET', 'POST'])
@csrf.exempt  # Exempt from CSRF for external cron services
@limiter.limit("10 per minute")
def check_deadlines_endpoint():
    # Verify API Key
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    expected_key = app.config['CRON_API_KEY']
    
    if not expected_key:
        logger.warning("⚠️ CRON_API_KEY not configured, endpoint is open!")
    elif api_key != expected_key:
        logger.warning(f"🚫 Unauthorized cron access attempt from {request.remote_addr}")
        return {'success': False, 'error': 'Unauthorized'}, 401
    
    try:
        count = notify_deadlines()
        logger.info(f"✅ Cron job completed. Sent {count} notification(s)")
        return {
            'success': True,
            'message': f'Sent {count} notification(s)',
            'timestamp': datetime.now().isoformat()
        }, 200
    except Exception as e:
        logger.error(f"❌ Cron job failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

# ---------------------------------------------------------
# Run Application
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )
