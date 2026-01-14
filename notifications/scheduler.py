"""
Notification Scheduler for ITRACK
Handles deadline checks and sends notifications
"""
import pandas as pd
from datetime import datetime
from flask import current_app
from models import get_db
from notifications.email_service import send_deadline_reminder, send_overdue_alert, send_assignment_email
import logging

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Notification thresholds
REMINDER_DAYS = [30, 15, 7, 0]  # Days before deadline to send reminders


def notify_deadlines():
    """
    Check all projects and send deadline notifications
    - 30, 15, 7, 0 days: reminder to Researcher
    - 7, 0 days: also notify Admin/Manager
    - Overdue: weekly notification to Researcher + Admin
    """
    logger.info("⏳ Starting deadline check job...")
    
    conn = get_db()
    today = datetime.today().date()
    count_sent = 0
    
    try:
        # Get all projects with deadlines
        projects = conn.execute("""
            SELECT rp.*, u.username as assigned_name, u.email as assigned_email
            FROM research_projects rp
            LEFT JOIN users u ON rp.assigned_researcher_id = u.id
        """).fetchall()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return 0
    
    # Get admin/manager emails
    try:
        admins = conn.execute("""
            SELECT email, username FROM users 
            WHERE role IN ('admin', 'manager') AND email IS NOT NULL AND email != ''
        """).fetchall()
    except:
        admins = []
    
    for row in projects:
        if not row['deadline']:
            continue
        
        # Determine email recipient
        recipient_email = row.get('assigned_email') or row.get('researcher_email')
        recipient_name = row.get('assigned_name') or row.get('researcher_name') or 'ผู้รับผิดชอบ'
        
        if not recipient_email:
            continue
        
        try:
            dt = pd.to_datetime(row['deadline'], errors='coerce')
            if pd.isna(dt):
                continue
            
            days_left = (dt.date() - today).days
            project_name = row['project_th'] or f"Project #{row['id']}"
            
            # Check if should notify
            should_notify_researcher = False
            should_notify_admin = False
            
            # Deadline reminders
            if days_left in REMINDER_DAYS:
                should_notify_researcher = True
                # Notify admins for urgent (7 days and deadline day)
                if days_left <= 7:
                    should_notify_admin = True
                logger.info(f"🔔 Deadline reminder: {project_name} ({days_left} days left)")
            
            # Overdue - weekly (every 7 days or first day)
            elif days_left < 0:
                days_overdue = abs(days_left)
                if days_overdue == 1 or days_overdue % 7 == 0:
                    should_notify_researcher = True
                    should_notify_admin = True
                    logger.info(f"❌ Overdue alert: {project_name} ({days_overdue} days overdue)")
            
            # Send notifications
            if should_notify_researcher:
                if days_left >= 0:
                    success, _ = send_deadline_reminder(
                        recipient_email, recipient_name, project_name, days_left
                    )
                else:
                    success, _ = send_overdue_alert(
                        recipient_email, recipient_name, project_name, 
                        abs(days_left), is_admin=False
                    )
                
                if success:
                    count_sent += 1
            
            if should_notify_admin:
                for admin in admins:
                    if admin['email']:
                        if days_left >= 0:
                            send_deadline_reminder(
                                admin['email'], admin['username'],
                                project_name, days_left
                            )
                        else:
                            send_overdue_alert(
                                admin['email'], admin['username'],
                                project_name, abs(days_left), is_admin=True
                            )
            
        except Exception as e:
            logger.error(f"Error processing project {row['id']}: {e}")
            continue
    
    logger.info(f"✅ Job finished. Sent {count_sent} emails.")
    return count_sent


def send_assignment_notification(researcher_id, project_id):
    """
    Send notification when researcher is assigned to a project
    Called from assign_researcher route
    """
    try:
        conn = get_db()
        
        # Get researcher info
        researcher = conn.execute(
            "SELECT username, email FROM users WHERE id = ?", (researcher_id,)
        ).fetchone()
        
        # Get project info
        project = conn.execute(
            "SELECT project_th FROM research_projects WHERE id = ?", (project_id,)
        ).fetchone()
        
        if researcher and researcher['email'] and project:
            success, error = send_assignment_email(
                researcher['email'],
                researcher['username'],
                project['project_th'] or f"Project #{project_id}",
                project_id
            )
            
            if success:
                logger.info(f"✅ Assignment notification sent to {researcher['email']}")
                return True
            else:
                logger.error(f"❌ Failed to send assignment email: {error}")
        else:
            logger.warning(f"⚠️ Cannot send assignment notification: missing data")
            
    except Exception as e:
        logger.error(f"❌ Assignment notification error: {e}")
    
    return False
