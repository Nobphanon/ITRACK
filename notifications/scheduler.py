import pandas as pd
from datetime import datetime
from flask import current_app
from models import get_db
from notifications.email_service import send_alert_email
import logging

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def notify_deadlines():
    """
    ฟังก์ชันสำหรับ Cron Job:
    1. ดึงโปรเจกต์ทั้งหมด
    2. เช็ควันหมดอายุ
    3. ส่งเมลถ้าวลาน้อยกว่า 7 วัน
    """
    logger.info("⏳ Starting deadline check job...")
    
    count_sent = 0
    conn = get_db()
    try:
        projects = conn.execute("SELECT * FROM research_projects").fetchall()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return 0
    finally:
        conn.close()

    today = datetime.today().date()

    for row in projects:
        # ข้ามถ้าไม่มีอีเมล หรือไม่มี Deadline
        if not row['researcher_email'] or not row['deadline']:
            continue

        try:
            # แปลงวันที่
            dt = pd.to_datetime(row['deadline'], errors='coerce')
            if pd.isna(dt):
                continue
            
            days_left = (dt.date() - today).days

            # ✅ เงื่อนไขการแจ้งเตือนอัตโนมัติ 
            # (เช่น แจ้งเตือนเมื่อเหลือ <= 7 วัน และยังไม่เลยกำหนด หรือแล้วแต่คุณจะตั้ง)
            if 0 <= days_left <= 7:
                logger.info(f"Checking Project: {row['project_th']} (Days left: {days_left})")
                
                # เรียกใช้บริการส่งอีเมล
                success, _ = send_alert_email(
                    row['researcher_email'], 
                    row['project_th'], 
                    days_left
                )
                
                if success:
                    count_sent += 1

        except Exception as e:
            logger.error(f"Error processing project {row['id']}: {e}")
            continue

    logger.info(f"✅ Job finished. Sent {count_sent} emails.")
    return count_sent