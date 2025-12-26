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

        # กันค่าว่าง
        if not username or not pw:
            flash('กรอกข้อมูลให้ครบ', 'danger')
            return render_template("auth/login.html")

        conn = get_db()
        user_row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if not user_row:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            return render_template("auth/login.html")

        # ป้องกัน type แปลก / None จาก production
        try:
            hashed = user_row['password']
        except Exception:
            flash('ระบบข้อมูลผู้ใช้ผิดพลาด', 'danger')
            return render_template("auth/login.html")

        if not isinstance(hashed, str):
            hashed = str(hashed)

        # ตรวจรหัสผ่านอย่างปลอดภัย
        if check_password_hash(hashed, pw):
            user = User(user_row['id'], user_row['username'], user_row['email'], user_row['role'])
            login_user(user)
            return redirect(url_for('research.landing'))

        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template("auth/login.html")

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
