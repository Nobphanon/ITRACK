from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import get_db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        pw = request.form.get('password')

        conn = get_db()
        user_row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user_row and check_password_hash(user_row['password'], pw):
            user = User(user_row['id'], user_row['username'], user_row['email'], user_row['role'])
            
            # ✅ Login เข้าไป (Session จะหายเมื่อปิด Browser ตามที่เราตั้งใน app.py)
            login_user(user)
            
            # ✅ เด้งไปหน้า Landing (index.html) ตามที่คุณต้องการ
            return redirect(url_for('research.landing'))

        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template("auth/login.html")

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))