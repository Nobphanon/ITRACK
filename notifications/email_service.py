import requests
import logging
from flask import current_app

logger = logging.getLogger(__name__)

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"

def send_alert_email(to_email, project_name, days_left):
    subject = "แจ้งเตือนกำหนดส่งโครงการวิจัย"

    content = f"""
เรียน ผู้รับผิดชอบโครงการ

ระบบ ITRACK ขอแจ้งเตือนสถานะโครงการวิจัยของท่าน ดังรายละเอียดต่อไปนี้

ชื่อโครงการ: {project_name}
สถานะ: เหลือเวลาอีก {days_left} วัน ก่อนถึงกำหนดส่ง

กรุณาดำเนินการตามแผนงานเพื่อให้แล้วเสร็จภายในระยะเวลาที่กำหนด

ขอแสดงความนับถือ

ITRACK Research Monitoring System
(ระบบแจ้งเตือนอัตโนมัติ)
"""

    payload = {
        "personalizations": [{
            "to": [{"email": to_email}]
        }],
        "from": {"email": current_app.config['MAIL_SENDER']},
        "subject": subject,
        "content": [{
            "type": "text/plain",
            "value": content
        }]
    }

    headers = {
        "Authorization": f"Bearer {current_app.config['SENDGRID_API_KEY']}",
        "Content-Type": "application/json"
    }

    r = requests.post(SENDGRID_API, json=payload, headers=headers)

    if r.status_code in [200, 202]:
        logger.info(f"✅ Email sent to {to_email}")
        return True, None
    else:
        logger.error(f"❌ SendGrid error: {r.text}")
        return False, r.text

