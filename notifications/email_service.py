from flask_mail import Message
from flask import current_app
from extensions import mail
from smtplib import SMTPException
import socket
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_alert_email(to_email, project_name, days_left):
    """
    Send project deadline alert email
    Returns: (success: bool, error_message: str or None)
    """
    if not to_email:
        logger.warning("⚠️ No recipient email")
        return False, "No recipient email"

    if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
        logger.error("❌ Mail configuration missing")
        return False, "Mail configuration missing"

    subject = f"🔔 แจ้งเตือน: โครงการ '{project_name}' ใกล้ถึงกำหนดส่งแล้ว"

    body_html = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
        <h2 style="color: #2c3e50;">เรียน นักวิจัย/ผู้รับผิดชอบโครงการ</h2>
        <p>ระบบ ITRACK ขอแจ้งเตือนสถานะโครงการวิจัยของท่าน ดังนี้:</p>
        <hr>
        <p><strong>📂 โครงการ:</strong> {project_name}</p>
        <p style="color: #e74c3c; font-size: 18px; font-weight: bold;">
            ⏳ เหลือเวลาอีก {days_left} วัน จะถึงกำหนดส่ง (Deadline)
        </p>
        <hr>
        <p style="color: #7f8c8d; font-size: 12px;">
            *จดหมายฉบับนี้ส่งจากระบบอัตโนมัติ กรุณาอย่าตอบกลับ
        </p>
    </div>
    """

    body_text = f"""
    เรียน นักวิจัย/ผู้รับผิดชอบโครงการ

    ระบบ ITRACK ขอแจ้งเตือนสถานะโครงการวิจัยของท่าน:

    📂 โครงการ: {project_name}
    ⏳ เหลือเวลาอีก {days_left} วัน จะถึงกำหนดส่ง (Deadline)

    *จดหมายฉบับนี้ส่งจากระบบอัตโนมัติ กรุณาอย่าตอบกลับ
    """

    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body_text,
            html=body_html
        )

        mail.send(msg)
        logger.info(f"✅ Sent email to {to_email}")
        return True, None

    except (SMTPException, socket.timeout, socket.error) as e:
        error_msg = str(e)
        logger.error(f"❌ Email send failed: {error_msg}")
        return False, error_msg


def test_email_config():
    """
    Debug email configuration
    """
    try:
        config = current_app.config
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
