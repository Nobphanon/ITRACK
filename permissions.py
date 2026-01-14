"""
Permission System for ITRACK
Role-based access control decorators and utilities
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def admin_required(f):
    """
    Decorator to restrict access to Admin role only.
    Usage: @admin_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'admin':
            flash('⛔ ต้องการสิทธิ์ Admin เท่านั้น', 'danger')
            return redirect(url_for('research.landing'))
        
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """
    Decorator to restrict access to Manager role (or Admin).
    Usage: @manager_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        
        if current_user.role not in ['admin', 'manager']:
            flash('⛔ ต้องการสิทธิ์ Manager หรือ Admin เท่านั้น', 'danger')
            return redirect(url_for('research.landing'))
        
        return f(*args, **kwargs)
    return decorated_function


def researcher_required(f):
    """
    Decorator to restrict access to Researcher role (or higher).
    Usage: @researcher_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        
        if current_user.role not in ['admin', 'manager', 'researcher']:
            flash('⛔ ไม่มีสิทธิ์เข้าถึง', 'danger')
            return redirect(url_for('research.landing'))
        
        return f(*args, **kwargs)
    return decorated_function


def roles_required(allowed_roles):
    """
    Decorator to restrict access to specific roles.
    Usage: @roles_required(['admin', 'manager'])
    
    Args:
        allowed_roles (list): List of role names that are allowed
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in allowed_roles:
                flash(f'⛔ ต้องการสิทธิ์: {", ".join(allowed_roles)}', 'danger')
                return redirect(url_for('research.landing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_admin():
    """Check if current user is Admin"""
    return current_user.is_authenticated and current_user.role == 'admin'


def is_manager():
    """Check if current user is Manager (or Admin)"""
    return current_user.is_authenticated and current_user.role in ['admin', 'manager']


def is_researcher():
    """Check if current user is Researcher"""
    return current_user.is_authenticated and current_user.role == 'researcher'


def can_manage_users():
    """Check if current user can manage users (Admin only)"""
    return is_admin()


def can_manage_projects():
    """Check if current user can manage projects (Admin or Manager)"""
    return current_user.is_authenticated and current_user.role in ['admin', 'manager']


def can_update_progress(project):
    """
    Check if current user can update progress for a specific project.
    
    Args:
        project: Project row object with assigned_researcher_id
    
    Returns:
        bool: True if user can update, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin and Manager can update any project
    if current_user.role in ['admin', 'manager']:
        return True
    
    # Researcher can only update their assigned projects
    if current_user.role == 'researcher':
        return project['assigned_researcher_id'] == current_user.id
    
    return False


def get_role_display_name(role):
    """Get Thai display name for role"""
    role_names = {
        'admin': 'ผู้ดูแลระบบ',
        'manager': 'ผู้จัดการ',
        'researcher': 'นักวิจัย'
    }
    return role_names.get(role, role)


def get_role_badge_class(role):
    """Get CSS badge class for role"""
    role_classes = {
        'admin': 'badge bg-danger',
        'manager': 'badge bg-warning text-dark',
        'researcher': 'badge bg-success'
    }
    return role_classes.get(role, 'badge bg-secondary')
