"""
Admin Routes - User Management
Admin-only functionality for managing users
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import get_db
from database import IS_POSTGRES
from permissions import admin_required
from audit.service import log_action
import re

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Get correct placeholder for current database
def ph():
    return '%s' if IS_POSTGRES else '?'


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, role
        FROM users
        ORDER BY 
            CASE role
                WHEN 'admin' THEN 1
                WHEN 'manager' THEN 2
                WHEN 'researcher' THEN 3
                ELSE 4
            END,
            username
    """)
    users = cursor.fetchall()
    
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create new user"""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'researcher')
    
    # Validation
    if not username or not email or not password:
        flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
        return redirect(url_for('admin.users'))
    
    # Validate username (alphanumeric and underscore only)
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        flash('Username ต้องมี 3-20 ตัวอักษร (a-z, 0-9, _)', 'danger')
        return redirect(url_for('admin.users'))
    
    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        flash('รูปแบบอีเมลไม่ถูกต้อง', 'danger')
        return redirect(url_for('admin.users'))
    
    # Validate role
    if role not in ['admin', 'manager', 'researcher']:
        flash('Role ไม่ถูกต้อง', 'danger')
        return redirect(url_for('admin.users'))
    
    # Check if username already exists
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id FROM users WHERE username = {ph()}", 
        (username,)
    )
    existing = cursor.fetchone()
    
    if existing:
        flash(f'Username "{username}" มีอยู่ในระบบแล้ว', 'danger')
        return redirect(url_for('admin.users'))
    
    # Check if email already exists
    cursor.execute(
        f"SELECT id FROM users WHERE email = {ph()}", 
        (email,)
    )
    existing_email = cursor.fetchone()
    
    if existing_email:
        flash(f'Email "{email}" มีอยู่ในระบบแล้ว', 'danger')
        return redirect(url_for('admin.users'))
    
    # Create user
    hashed_password = generate_password_hash(password)
    try:
        cursor.execute(f"""
            INSERT INTO users (username, email, password, role)
            VALUES ({ph()}, {ph()}, {ph()}, {ph()})
        """, (username, email, hashed_password, role))
        conn.commit()
        
        log_action('USER_CREATED', 'user', None, f'Created user: {username} ({role})')
        flash(f'✅ สร้างผู้ใช้ "{username}" สำเร็จ', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user"""
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'researcher')
    
    # Validation
    if not email:
        flash('กรุณากรอกอีเมล', 'danger')
        return redirect(url_for('admin.users'))
    
    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        flash('รูปแบบอีเมลไม่ถูกต้อง', 'danger')
        return redirect(url_for('admin.users'))
    
    # Validate role
    if role not in ['admin', 'manager', 'researcher']:
        flash('Role ไม่ถูกต้อง', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent editing yourself if changing to non-admin
    if user_id == current_user.id and role != 'admin':
        flash('⚠️ คุณไม่สามารถเปลี่ยน role ของตัวเองได้', 'danger')
        return redirect(url_for('admin.users'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute(f"SELECT username FROM users WHERE id = {ph()}", (user_id,))
    user = cursor.fetchone()
    if not user:
        flash('ไม่พบผู้ใช้', 'danger')
        return redirect(url_for('admin.users'))
    
    # Check if email already exists (exclude current user)
    cursor.execute(
        f"SELECT id FROM users WHERE email = {ph()} AND id != {ph()}", 
        (email, user_id)
    )
    existing_email = cursor.fetchone()
    
    if existing_email:
        flash(f'Email "{email}" มีอยู่ในระบบแล้ว', 'danger')
        return redirect(url_for('admin.users'))
    
    # Update user
    try:
        cursor.execute(f"""
            UPDATE users 
            SET email = {ph()}, role = {ph()}
            WHERE id = {ph()}
        """, (email, role, user_id))
        conn.commit()
        
        log_action('USER_UPDATED', 'user', user_id, f'Updated user: {user["username"]} to {role}')
        flash(f'✅ อัปเดตผู้ใช้ "{user["username"]}" สำเร็จ', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user"""
    # Prevent deleting yourself
    if user_id == current_user.id:
        flash('⚠️ คุณไม่สามารถลบตัวเองได้', 'danger')
        return redirect(url_for('admin.users'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT username FROM users WHERE id = {ph()}", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash('ไม่พบผู้ใช้', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        # Delete user
        cursor.execute(f"DELETE FROM users WHERE id = {ph()}", (user_id,))
        conn.commit()
        
        log_action('USER_DELETED', 'user', user_id, f'Deleted user: {user["username"]}')
        flash(f'✅ ลบผู้ใช้ "{user["username"]}" สำเร็จ', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """Reset user password"""
    new_password = request.form.get('new_password', '').strip()
    
    if not new_password:
        flash('กรุณากรอกรหัสผ่านใหม่', 'danger')
        return redirect(url_for('admin.users'))
    
    if len(new_password) < 3:
        flash('รหัสผ่านต้องมีอย่างน้อย 3 ตัวอักษร', 'danger')
        return redirect(url_for('admin.users'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT username FROM users WHERE id = {ph()}", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash('ไม่พบผู้ใช้', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        hashed_password = generate_password_hash(new_password)
        cursor.execute(f"""
            UPDATE users 
            SET password = {ph()}
            WHERE id = {ph()}
        """, (hashed_password, user_id))
        conn.commit()
        
        log_action('PASSWORD_RESET', 'user', user_id, f'Reset password for: {user["username"]}')
        flash(f'✅ รีเซ็ตรหัสผ่านผู้ใช้ "{user["username"]}" สำเร็จ', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('admin.users'))
