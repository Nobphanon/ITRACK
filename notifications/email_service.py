from flask_mail import Message
from extensions import mail
from smtplib import SMTPException
import socket
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_alert_email(to_email, project_name, days_left):
    if not to_email:
        logger.warning("⚠️ No recipient email")
        return False, "No recipient email"

    subject = f"🔔 แจ้งเตือน: โครงการ '{project_name}' ใกล้ถึงกำหนดส่งแล้ว"

    body_html = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
        <h2>เรียน นักวิจัย/ผู้รับผิดชอบโครงการ</h2>
        <p><strong>โครงการ:</strong> {project_name}</p>
        <p style="color:red;">⏳ เหลือเวลาอีก {days_left} วัน จะถึงกำหนดส่ง</p>
        <p style="font-size:12px;">*ส่งจากระบบอัตโนมัติ กรุณาอย่าตอบกลับ</p>
    </div>
    """

    body_text = f"""
โครงการ: {project_name}
เหลือเวลาอีก {days_left} วัน จะถึงกำหนดส่ง
"""

    try:
        from app import app  # 🔥 บังคับใช้ main Flask app context

        with app.app_context():
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body_text,
                html=body_html
            )
            mail.send(msg)

        logger.info(f"✅ Sent email to {to_email}")
        return True, None

    except (SMTPException, socket.timeout, socket.error, Exception) as e:
        logger.error(f"❌ Email send failed: {e}")
        return False, str(e)


def test_email_config():
    try:
        from app import app
        with app.app_context():
            config = app.config
            logger.info("=== Email Configuration ===")
            logger.info(f"MAIL_SERVER: {config.get('MAIL_SERVER')}")
            logger.info(f"MAIL_PORT: {config.get('MAIL_PORT')}")
            logger.info(f"MAIL_USE_TLS: {config.get('MAIL_USE_TLS')}")
            logger.info(f"MAIL_USERNAME: {config.get('MAIL_USERNAME')}")
            logger.info(f"MAIL_PASSWORD: {'***' if config.get('MAIL_PASSWORD') else 'NOT SET'}")
            logger.info("===========================")

            if not config.get('MAIL_USERNAME') or not config.get('MAIL_PASSWORD'):
                return False, "MAIL_USERNAME or MAIL_PASSWORD not configured"

        return True, "Configuration looks good"

    except Exception as e:
        return False, str(e)
