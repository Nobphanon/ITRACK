"""
Notification Routes - API endpoints for in-app notifications
"""
from flask import Blueprint, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user
from notifications.notification_service import (
    get_notifications, 
    get_unread_count, 
    mark_as_read, 
    mark_all_read
)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/')
@login_required
def index():
    """หน้าแสดง notifications ทั้งหมด"""
    notifications = get_notifications(current_user.id, limit=50)
    unread_count = get_unread_count(current_user.id)
    
    return render_template('notifications/index.html',
                          notifications=notifications,
                          unread_count=unread_count)


@notifications_bp.route('/api/list')
@login_required
def api_list():
    """API: ดึงรายการ notifications"""
    limit = 10
    notifications = get_notifications(current_user.id, limit=limit)
    
    return jsonify({
        'success': True,
        'notifications': notifications,
        'count': len(notifications)
    })


@notifications_bp.route('/api/count')
@login_required
def api_count():
    """API: นับจำนวนที่ยังไม่อ่าน"""
    count = get_unread_count(current_user.id)
    
    return jsonify({
        'success': True,
        'count': count
    })


@notifications_bp.route('/api/<int:notif_id>/read', methods=['POST'])
@login_required
def api_mark_read(notif_id):
    """API: ทำเครื่องหมายว่าอ่านแล้ว"""
    success = mark_as_read(notif_id, current_user.id)
    
    return jsonify({
        'success': success
    })


@notifications_bp.route('/api/read-all', methods=['POST'])
@login_required
def api_mark_all_read():
    """API: ทำเครื่องหมายว่าอ่านแล้วทั้งหมด"""
    count = mark_all_read(current_user.id)
    
    return jsonify({
        'success': True,
        'updated': count
    })


@notifications_bp.route('/click/<int:notif_id>')
@login_required
def click_notification(notif_id):
    """คลิก notification - mark as read และ redirect"""
    from models import get_db
    
    conn = get_db()
    notification = conn.execute(
        "SELECT * FROM notifications WHERE id = ? AND user_id = ?",
        (notif_id, current_user.id)
    ).fetchone()
    
    if notification:
        mark_as_read(notif_id, current_user.id)
        
        if notification['link']:
            return redirect(notification['link'])
    
    # Fallback: กลับหน้า notifications
    return redirect(url_for('notifications.index'))
