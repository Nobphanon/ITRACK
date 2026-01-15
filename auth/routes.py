from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import get_db, User, execute_query
from database import IS_POSTGRES
from extensions import limiter
from audit.service import log_login_attempt, log_action

auth_bp = Blueprint('auth', __name__)

# Get correct placeholder for current database
def ph():
    return '%s' if IS_POSTGRES else '?'


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
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
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM users WHERE username = {ph()}",
            (username,)
        )
        user_row = cursor.fetchone()

        if not user_row:
            log_login_attempt(username, success=False)
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            return render_template("auth/login.html")

        # Handle both dict-like and tuple-like row access
        if IS_POSTGRES:
            hashed = str(user_row['password'])
            user = User(user_row['id'], user_row['username'], user_row['email'], user_row['role'])
        else:
            hashed = str(user_row['password'])
            user = User(user_row['id'], user_row['username'], user_row['email'], user_row['role'])

        if check_password_hash(hashed, pw):
            login_user(user)
            log_login_attempt(username, success=True)
            
            # Role-based redirect after login
            if user.role == 'researcher':
                return redirect(url_for('researcher.dashboard'))
            else:
                return redirect(url_for('research.landing'))

        log_login_attempt(username, success=False)
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template("auth/login.html")



@auth_bp.route('/logout')
@login_required
def logout():
    """
    Handle user logout.
    """
    log_action("LOGOUT")
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
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT password FROM users WHERE id = {ph()}",
            (current_user.id,)
        )
        user_row = cursor.fetchone()

        if not user_row or not check_password_hash(str(user_row['password']), old):
            flash('รหัสผ่านเดิมไม่ถูกต้อง', 'danger')
            return redirect(url_for('auth.change_password'))

        if new != confirm:
            flash('รหัสผ่านใหม่ไม่ตรงกัน', 'danger')
            return redirect(url_for('auth.change_password'))

        hashed = generate_password_hash(new)
        cursor.execute(f"UPDATE users SET password = {ph()} WHERE id = {ph()}", (hashed, current_user.id))
        conn.commit()

        log_action("PASSWORD_CHANGED")
        flash('เปลี่ยนรหัสผ่านเรียบร้อยแล้ว', 'success')
        
        # Role-based redirect after password change
        if current_user.role == 'researcher':
            return redirect(url_for('researcher.dashboard'))
        else:
            return redirect(url_for('research.landing'))

    return render_template('auth/change_password.html')