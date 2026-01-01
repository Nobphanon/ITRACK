import sqlite3
import pandas as pd
from datetime import datetime
import logging

from notifications.email_service import send_alert_email

DB_NAME = "database.db"

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def notify_deadlines():
    """
    ตรวจสอบและส่งการแจ้งเตือนสำหรับโครงการที่ใกล้ครบกำหนด
    """
    logger.info("🔍 เริ่มตรวจสอบ deadlines...")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, researcher_email, project_title, deadline
            FROM research_projects
            WHERE researcher_email IS NOT NULL
        """)
        projects = cur.fetchall()

        if not projects:
            logger.info("ℹ️ ไม่พบโครงการที่ต้องตรวจสอบ")
            conn.close()
            return

        today = datetime.today().date()
        notifications_sent = 0

        for project_id, email, title, deadline_str in projects:
            try:
                deadline_date = pd.to_datetime(deadline_str, errors="coerce")
                if pd.isna(deadline_date):
                    logger.warning(f"⚠️ โครงการ ID {project_id} มี deadline ไม่ถูกต้อง: {deadline_str}")
                    continue

                days_left = (deadline_date.date() - today).days

                # ===========================
                # แจ้งเตือน 7 วันก่อน
                # ===========================
                if days_left == 7:
                    cur.execute("""
                        SELECT 1 FROM notification_log
                        WHERE project_id = ? AND notify_type = '7_days'
                    """, (project_id,))
                    already_sent = cur.fetchone()

                    if not already_sent:
                        success, error = send_alert_email(email, title, days_left)
                        
                        if success:
                            cur.execute("""
                                INSERT INTO notification_log
                                (project_id, notify_type, sent_at)
                                VALUES (?, '7_days', datetime('now'))
                            """, (project_id,))
                            logger.info(f"✅ ส่งการแจ้งเตือน 7 วัน ไปยัง {email} (โครงการ: {title})")
                            notifications_sent += 1
                        else:
                            logger.error(f"❌ ส่งอีเมลล้มเหลว: {error}")

                # ===========================
                # แจ้งเตือนวันครบกำหนด
                # ===========================
                elif days_left == 0:
                    cur.execute("""
                        SELECT 1 FROM notification_log
                        WHERE project_id = ? AND notify_type = 'due_date'
                    """, (project_id,))
                    already_sent = cur.fetchone()

                    if not already_sent:
                        success, error = send_alert_email(email, title, days_left)
                        
                        if success:
                            cur.execute("""
                                INSERT INTO notification_log
                                (project_id, notify_type, sent_at)
                                VALUES (?, 'due_date', datetime('now'))
                            """, (project_id,))
                            logger.info(f"✅ ส่งการแจ้งเตือนวันครบกำหนด ไปยัง {email} (โครงการ: {title})")
                            notifications_sent += 1
                        else:
                            logger.error(f"❌ ส่งอีเมลล้มเหลว: {error}")

            except Exception as e:
                logger.error(f"❌ เกิดข้อผิดพลาดกับโครงการ ID {project_id}: {str(e)}")
                continue

        conn.commit()
        conn.close()
        
        logger.info(f"✅ ตรวจสอบเสร็จสิ้น - ส่งการแจ้งเตือนทั้งหมด {notifications_sent} รายการ")
        return notifications_sent

    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาดในการตรวจสอบ deadlines: {str(e)}")
        return 0