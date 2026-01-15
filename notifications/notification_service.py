"""
Notification Service - In-app notifications management
"""
import logging
from datetime import datetime
from models import get_db
from database import IS_POSTGRES

logger = logging.getLogger(__name__)


def create_notification(user_id, title, message=None, notif_type='info', link=None):
    """
    สร้าง notification ใหม่สำหรับ user
    
    Args:
        user_id: ID ของผู้ใช้ที่จะรับ notification
        title: หัวข้อ notification
        message: รายละเอียดเพิ่มเติม (optional)
        notif_type: ประเภท (info, warning, danger, success)
        link: URL ที่จะ redirect เมื่อคลิก (optional)
    
    Returns:
        int: notification ID หรือ None ถ้าล้มเหลว
    """
    try:
        conn = get_db()
        now = datetime.now().isoformat()
        
        cursor = conn.execute("""
            INSERT INTO notifications (user_id, title, message, type, link, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
        """, (user_id, title, message, notif_type, link, now))
        
        conn.commit()
        
        # Get the inserted ID
        if IS_POSTGRES:
            # PostgreSQL needs to return the ID differently
            notif_id = cursor.fetchone()
        else:
            notif_id = cursor.lastrowid
            
        logger.info(f"🔔 Created notification for user {user_id}: {title}")
        return notif_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create notification: {e}")
        return None


def create_notification_for_role(role, title, message=None, notif_type='info', link=None):
    """
    สร้าง notification สำหรับผู้ใช้ทุกคนที่มี role ที่กำหนด
    
    Args:
        role: 'admin', 'manager', หรือ 'researcher'
        title, message, notif_type, link: เหมือน create_notification
    
    Returns:
        int: จำนวน notifications ที่สร้าง
    """
    try:
        conn = get_db()
        users = conn.execute(
            "SELECT id FROM users WHERE role = ?", (role,)
        ).fetchall()
        
        count = 0
        for user in users:
            if create_notification(user['id'], title, message, notif_type, link):
                count += 1
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to create notifications for role {role}: {e}")
        return 0


def get_notifications(user_id, limit=20, unread_only=False):
    """
    ดึง notifications ของ user
    
    Args:
        user_id: ID ของผู้ใช้
        limit: จำนวนสูงสุดที่จะดึง
        unread_only: ดึงเฉพาะที่ยังไม่อ่าน
    
    Returns:
        list: รายการ notifications
    """
    try:
        conn = get_db()
        
        sql = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]
        
        if unread_only:
            sql += " AND is_read = 0"
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        notifications = conn.execute(sql, params).fetchall()
        return [dict(n) for n in notifications]
        
    except Exception as e:
        logger.error(f"❌ Failed to get notifications: {e}")
        return []


def get_unread_count(user_id):
    """
    นับจำนวน notifications ที่ยังไม่อ่าน
    
    Args:
        user_id: ID ของผู้ใช้
    
    Returns:
        int: จำนวนที่ยังไม่อ่าน
    """
    try:
        conn = get_db()
        result = conn.execute(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()
        
        return result['count'] if result else 0
        
    except Exception as e:
        logger.error(f"❌ Failed to get unread count: {e}")
        return 0


def mark_as_read(notification_id, user_id=None):
    """
    ทำเครื่องหมายว่าอ่านแล้ว
    
    Args:
        notification_id: ID ของ notification
        user_id: ID ของผู้ใช้ (สำหรับ security check)
    
    Returns:
        bool: สำเร็จหรือไม่
    """
    try:
        conn = get_db()
        
        if user_id:
            conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
                (notification_id, user_id)
            )
        else:
            conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (notification_id,)
            )
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to mark as read: {e}")
        return False


def mark_all_read(user_id):
    """
    ทำเครื่องหมายว่าอ่านแล้วทั้งหมด
    
    Args:
        user_id: ID ของผู้ใช้
    
    Returns:
        int: จำนวนที่ถูกอัปเดต
    """
    try:
        conn = get_db()
        cursor = conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (user_id,)
        )
        conn.commit()
        
        return cursor.rowcount if hasattr(cursor, 'rowcount') else 0
        
    except Exception as e:
        logger.error(f"❌ Failed to mark all as read: {e}")
        return 0


def delete_old_notifications(days=30):
    """
    ลบ notifications เก่ากว่า X วัน
    
    Args:
        days: จำนวนวันที่เก็บไว้
    
    Returns:
        int: จำนวนที่ลบ
    """
    try:
        conn = get_db()
        
        if IS_POSTGRES:
            cursor = conn.execute("""
                DELETE FROM notifications 
                WHERE created_at < NOW() - INTERVAL '%s days'
            """, (days,))
        else:
            cursor = conn.execute("""
                DELETE FROM notifications 
                WHERE created_at < datetime('now', ?)
            """, (f'-{days} days',))
        
        conn.commit()
        count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
        
        if count > 0:
            logger.info(f"🗑️ Deleted {count} old notifications")
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to delete old notifications: {e}")
        return 0
