import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_login import LoginManager
from models import init_db, get_db, User
from extensions import mail 

# ================== 🧱 App Setup ==================
app = Flask(__name__)

# ================== 🔐 Security ==================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SESSION_PERMANENT'] = False

# ================== 📧 Mail Config ==================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kissmemore248@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('ITRACK Alert', app.config['MAIL_USERNAME'])

mail.init_app(app)

# ================== 👤 Login ==================
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

# ================== 🧩 Blueprints ==================
from auth.routes import auth_bp
from Research.routes import research_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(research_bp)

# ================== 🗄️ Database Init ==================
with app.app_context():
    init_db()

# ================== ▶️ Run Local ==================
if __name__ == "__main__":
    app.run(debug=True)
