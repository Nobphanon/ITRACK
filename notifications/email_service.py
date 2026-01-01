import requests
import logging

logger = logging.getLogger(__name__)

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"

def send_alert_email(to_email, project_name, days_left):
    from app import app

    subject = f"🔔 แจ้งเตือน: โครงการ '{project_name}' ใกล้ถึงกำหนดส่งแล้ว"

    content = f"""
    โครงการ: {project_name}
    เหลือเวลาอีก {days_left} วัน
    """

    payload = {
        "personalizations": [{
            "to": [{"email": to_email}]
        }],
        "from": {"email": app.config['MAIL_SENDER']},
        "subject": subject,
        "content": [{
            "type": "text/plain",
            "value": content
        }]
    }

    headers = {
        "Authorization": f"Bearer {app.config['SENDGRID_API_KEY']}",
        "Content-Type": "application/json"
    }

    r = requests.post(SENDGRID_API, json=payload, headers=headers)

    if r.status_code in [200, 202]:
        logger.info(f"✅ Email sent to {to_email}")
        return True, None
    else:
        logger.error(f"❌ SendGrid error: {r.text}")
        return False, r.text
