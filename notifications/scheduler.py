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
    logger.info("⏳ Starting deadline check job...")

    ALERT_DAYS = {7, 3, 0}
    count_sent = 0

    conn = get_db()
    try:
        projects = conn.execute("SELECT * FROM research_projects").fetchall()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return 0

    today = datetime.today().date()

    for row in projects:
        if not row['researcher_email'] or not row['deadline']:
            continue

        try:
            dt = pd.to_datetime(row['deadline'], errors='coerce')
            if pd.isna(dt):
                continue

            days_left = (dt.date() - today).days

            if days_left in ALERT_DAYS:
                logger.info(f"🔔 Alerting: {row['project_th']} ({days_left} days left)")

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

    conn.close()
    logger.info(f"✅ Job finished. Sent {count_sent} emails.")
    return count_sent
