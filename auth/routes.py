from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import get_db, User

auth_bp = Blueprint('auth', __name__)



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        pw = request.form.get('password')

        if not username or not pw:
            flash('กรอกข้อมูลให้ครบ', 'danger')
            return render_template("auth/login.html")

        conn = get_db()
        user_row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        # conn.close() removed (handled by teardown)

        if not user_row:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            return render_template("auth/login.html")

        hashed = str(user_row['password'])

        if check_password_hash(hashed, pw):
            user = User(user_row['id'], user_row['username'], user_row['email'], user_row['role'])
            login_user(user)
            return redirect(url_for('research.landing'))

        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template("auth/login.html")



@auth_bp.route('/logout')
@login_required
def logout():
    """
    Handle user logout.
    """
    logout_user()
    return redirect(url_for('auth.login'))



@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Handle password change for logged-in users.
    """
    if request.method == 'POST':
        old = request.form.get('old_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')

        conn = get_db()
        user_row = conn.execute(
            "SELECT password FROM users WHERE id = ?",
            (current_user.id,)
        ).fetchone()

        if not user_row or not check_password_hash(str(user_row['password']), old):
            # conn.close()
            flash('รหัสผ่านเดิมไม่ถูกต้อง', 'danger')
            return redirect(url_for('auth.change_password'))

        if new != confirm:
            # conn.close()
            flash('รหัสผ่านใหม่ไม่ตรงกัน', 'danger')
            return redirect(url_for('auth.change_password'))

        hashed = generate_password_hash(new)
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, current_user.id))
        conn.commit()
        # conn.close()

        flash('เปลี่ยนรหัสผ่านเรียบร้อยแล้ว', 'success')
        return redirect(url_for('research.landing'))

    return render_template('auth/change_password.html')
    