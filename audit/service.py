"""
Audit Service - Logging user actions for security and compliance
"""
import logging
from datetime import datetime
from flask import request
from flask_login import current_user
from models import get_db

logger = logging.getLogger(__name__)


def log_action(action, target_type=None, target_id=None, details=None):
    """
    บันทึก audit log ลงฐานข้อมูล
    
    Args:
        action: ชื่อ action เช่น LOGIN_SUCCESS, PROJECT_CREATED
        target_type: ประเภทของเป้าหมาย เช่น 'project', 'user'
        target_id: ID ของเป้าหมาย
        details: รายละเอียดเพิ่มเติม (string)
    """
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO audit_logs (timestamp, user_id, username, action, target_type, target_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            current_user.id if current_user.is_authenticated else None,
            current_user.username if current_user.is_authenticated else None,
            action,
            target_type,
            target_id,
            details,
            request.remote_addr if request else None
        ))
        conn.commit()
        logger.info(f"📝 Audit: {action} by {current_user.username if current_user.is_authenticated else 'anonymous'}")
    except Exception as e:
        logger.error(f"❌ Audit log error: {e}")


def log_login_attempt(username, success):
    """บันทึกการพยายาม login"""
    action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
    log_action(action, target_type="user", details=f"username: {username}")


def log_project_action(action, project_id=None, details=None):
    """บันทึก action เกี่ยวกับโครงการ"""
    log_action(action, target_type="project", target_id=project_id, details=details)


def get_audit_logs(limit=100, user_id=None, action=None):
    """
    ดึงประวัติ audit logs
    
    Args:
        limit: จำนวนรายการสูงสุด (default: 100)
        user_id: กรอง by user ID (optional)
        action: กรอง by action type (optional)
    
    Returns:
        list of audit log entries
    """
    conn = get_db()
    
    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if user_id:
        sql += " AND user_id = ?"
        params.append(user_id)
    
    if action:
        sql += " AND action = ?"
        params.append(action)
    
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    return conn.execute(sql, params).fetchall()
