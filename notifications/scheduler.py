import sqlite3
import pandas as pd
from datetime import datetime
import schedule
import time

from notifications.email_service import send_email

DB_NAME = "database.db"

def run_scheduler():
    print("Scheduler started")


def notify_deadlines():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, researcher_email, project_title, deadline
        FROM research_projects
    """)
    projects = cur.fetchall()

    today = datetime.today().date()

    for project_id, email, title, deadline_str in projects:
        deadline_date = pd.to_datetime(deadline_str, errors="coerce")
        if pd.isna(deadline_date):
            continue

        days_left = (deadline_date.date() - today).days

        # ===============================
        # แจ้งเตือน 7 วันก่อน (ครั้งเดียว)
        # ===============================
        if days_left == 7:
            cur.execute("""
                SELECT 1 FROM notification_log
                WHERE project_id = ? AND notify_type = '7_days'
            """, (project_id,))
            already_sent = cur.fetchone()

            if not already_sent:
                send_email(
                    email,
                    "⏰ Research Deadline Reminder (7 days left)",
                    f"""Project: {title}
Deadline: {deadline_str}

Remaining: 7 days
"""
                )
                cur.execute("""
                    INSERT INTO notification_log
                    (project_id, notify_type, sent_at)
                    VALUES (?, '7_days', datetime('now'))
                """, (project_id,))

        # ===============================
        # แจ้งเตือนวันครบกำหนด (ครั้งเดียว)
        # ===============================
        if days_left == 0:
            cur.execute("""
                SELECT 1 FROM notification_log
                WHERE project_id = ? AND notify_type = 'due_date'
            """, (project_id,))
            already_sent = cur.fetchone()

            if not already_sent:
                send_email(
                    email,
                    "🚨 Research Deadline Today",
                    f"""Project: {title}
Deadline: {deadline_str}

⚠ Today is the deadline.
"""
                )
                cur.execute("""
                    INSERT INTO notification_log
                    (project_id, notify_type, sent_at)
                    VALUES (?, 'due_date', datetime('now'))
                """, (project_id,))

    conn.commit()
    conn.close()


# ===============================
# Scheduler (รันทุกวัน 06:00)
# ===============================
def run_scheduler():
    schedule.every().day.at("06:00").do(notify_deadlines)

    while True:
        schedule.run_pending()
        time.sleep(60)
