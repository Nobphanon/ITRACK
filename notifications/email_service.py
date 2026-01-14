import requests
import logging
from flask import current_app
from datetime import datetime

logger = logging.getLogger(__name__)

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"

# ---------------------------------------------------------
# 📧 Email Sending Core
# ---------------------------------------------------------
def _send_email(to_email, subject, html_content, text_content=None):
    """Core function to send email via SendGrid"""
    try:
        api_key = current_app.config.get('SENDGRID_API_KEY')
        sender = current_app.config.get('MAIL_SENDER', 'noreply@itrack.local')
        
        if not api_key:
            logger.warning("⚠️ SENDGRID_API_KEY not configured, skipping email")
            return False, "API key not configured"
        
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": sender, "name": "ITRACK System"},
            "subject": subject,
            "content": [
                {"type": "text/html", "value": html_content}
            ]
        }
        
        if text_content:
            payload["content"].append({"type": "text/plain", "value": text_content})
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        r = requests.post(SENDGRID_API, json=payload, headers=headers, timeout=10)
        
        if r.status_code in [200, 202]:
            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return True, None
        else:
            logger.error(f"❌ SendGrid error: {r.text}")
            return False, r.text
    except Exception as e:
        logger.error(f"❌ Email error: {str(e)}")
        return False, str(e)


# ---------------------------------------------------------
# 📨 Email Templates
# ---------------------------------------------------------
def _get_email_template(title, content_html, accent_color="#3b82f6"):
    """Generate beautiful HTML email template"""
    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background:{accent_color};padding:24px;text-align:center;">
                            <h1 style="color:white;margin:0;font-size:24px;">📋 ITRACK</h1>
                            <p style="color:rgba(255,255,255,0.9);margin:8px 0 0 0;font-size:14px;">Research Project Management</p>
                        </td>
                    </tr>
                    <!-- Title -->
                    <tr>
                        <td style="padding:24px 24px 0;">
                            <h2 style="color:#1e293b;margin:0;font-size:20px;">{title}</h2>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding:16px 24px 24px;">
                            {content_html}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background:#f8fafc;padding:16px 24px;border-top:1px solid #e2e8f0;">
                            <p style="color:#64748b;font-size:12px;margin:0;text-align:center;">
                                ระบบแจ้งเตือนอัตโนมัติ | ITRACK Research Monitoring System<br>
                                {datetime.now().strftime('%d/%m/%Y %H:%M')}
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''


# ---------------------------------------------------------
# 🆕 Assignment Notification
# ---------------------------------------------------------
def send_assignment_email(to_email, researcher_name, project_name, project_id):
    """Notify researcher when assigned to a project"""
    subject = f"🆕 คุณได้รับมอบหมายโครงการใหม่: {project_name[:50]}"
    
    content_html = f'''
    <p style="color:#475569;line-height:1.6;">เรียน <strong>{researcher_name}</strong>,</p>
    <p style="color:#475569;line-height:1.6;">ระบบ ITRACK ขอแจ้งให้ทราบว่าคุณได้รับมอบหมายให้รับผิดชอบโครงการวิจัยใหม่:</p>
    
    <div style="background:#f0f9ff;border-left:4px solid #0ea5e9;padding:16px;margin:16px 0;border-radius:0 8px 8px 0;">
        <p style="margin:0;color:#0369a1;font-weight:bold;font-size:16px;">📁 {project_name}</p>
    </div>
    
    <p style="color:#475569;line-height:1.6;">กรุณาเข้าสู่ระบบเพื่อตรวจสอบรายละเอียดและอัปเดตความคืบหน้าของโครงการ</p>
    
    <p style="color:#475569;line-height:1.6;">ขอแสดงความนับถือ,<br><strong>ทีมบริหารจัดการโครงการวิจัย</strong></p>
    '''
    
    html = _get_email_template("📬 มอบหมายโครงการใหม่", content_html, "#0ea5e9")
    return _send_email(to_email, subject, html)


# ---------------------------------------------------------
# ⏰ Deadline Reminder
# ---------------------------------------------------------
def send_deadline_reminder(to_email, recipient_name, project_name, days_left, researcher_email=None):
    """Send deadline reminder based on days left"""
    
    # Determine urgency and color
    if days_left == 30:
        emoji = "📅"
        urgency = "แจ้งเตือนล่วงหน้า"
        accent_color = "#10b981"  # Green
        urgency_text = f"เหลือเวลาอีก <strong>30 วัน</strong>"
    elif days_left == 15:
        emoji = "⚠️"
        urgency = "แจ้งเตือน 15 วัน"
        accent_color = "#f59e0b"  # Yellow
        urgency_text = f"เหลือเวลาอีก <strong>15 วัน</strong>"
    elif days_left == 7:
        emoji = "🔶"
        urgency = "แจ้งเตือนด่วน"
        accent_color = "#f97316"  # Orange
        urgency_text = f"<span style='color:#dc2626;'>เหลือเวลาอีกเพียง <strong>7 วัน</strong></span>"
    elif days_left == 0:
        emoji = "🔴"
        urgency = "ถึงกำหนดส่งวันนี้!"
        accent_color = "#dc2626"  # Red
        urgency_text = "<span style='color:#dc2626;font-weight:bold;'>ถึงกำหนดส่ง วันนี้!</span>"
    else:
        emoji = "📅"
        urgency = "แจ้งเตือน Deadline"
        accent_color = "#6366f1"
        urgency_text = f"เหลือเวลาอีก <strong>{days_left} วัน</strong>"
    
    subject = f"{emoji} {urgency}: {project_name[:40]}"
    
    content_html = f'''
    <p style="color:#475569;line-height:1.6;">เรียน <strong>{recipient_name}</strong>,</p>
    <p style="color:#475569;line-height:1.6;">ระบบ ITRACK ขอแจ้งเตือนสถานะโครงการวิจัย:</p>
    
    <div style="background:#fef2f2;border-left:4px solid {accent_color};padding:16px;margin:16px 0;border-radius:0 8px 8px 0;">
        <p style="margin:0 0 8px 0;color:#1e293b;font-weight:bold;font-size:16px;">📁 {project_name}</p>
        <p style="margin:0;color:#475569;">{urgency_text}</p>
    </div>
    
    <p style="color:#475569;line-height:1.6;">กรุณาดำเนินการตามแผนงานเพื่อให้แล้วเสร็จภายในระยะเวลาที่กำหนด</p>
    
    <p style="color:#475569;line-height:1.6;">ขอแสดงความนับถือ,<br><strong>ITRACK System</strong></p>
    '''
    
    html = _get_email_template(f"{emoji} {urgency}", content_html, accent_color)
    return _send_email(to_email, subject, html)


# ---------------------------------------------------------
# ❌ Overdue Alert
# ---------------------------------------------------------
def send_overdue_alert(to_email, recipient_name, project_name, days_overdue, is_admin=False):
    """Send overdue alert (weekly)"""
    subject = f"❌ โครงการเลยกำหนดส่ง {days_overdue} วัน: {project_name[:40]}"
    
    admin_note = ""
    if is_admin:
        admin_note = '''
        <div style="background:#fef3c7;border:1px solid #f59e0b;padding:12px;margin:16px 0;border-radius:8px;">
            <p style="margin:0;color:#92400e;font-size:14px;">
                ⚠️ <strong>หมายเหตุสำหรับผู้ดูแล:</strong> โครงการนี้เลยกำหนดส่ง กรุณาติดตามผู้รับผิดชอบ
            </p>
        </div>
        '''
    
    content_html = f'''
    <p style="color:#475569;line-height:1.6;">เรียน <strong>{recipient_name}</strong>,</p>
    <p style="color:#475569;line-height:1.6;">ระบบ ITRACK ขอแจ้งเตือนว่าโครงการต่อไปนี้เลยกำหนดส่งแล้ว:</p>
    
    <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:16px;margin:16px 0;border-radius:0 8px 8px 0;">
        <p style="margin:0 0 8px 0;color:#1e293b;font-weight:bold;font-size:16px;">📁 {project_name}</p>
        <p style="margin:0;color:#dc2626;font-weight:bold;">❌ เลยกำหนดส่งแล้ว {days_overdue} วัน</p>
    </div>
    
    {admin_note}
    
    <p style="color:#475569;line-height:1.6;">กรุณาเร่งดำเนินการหรือติดต่อทีมบริหารเพื่อแจ้งเหตุผลที่ล่าช้า</p>
    
    <p style="color:#475569;line-height:1.6;">ขอแสดงความนับถือ,<br><strong>ITRACK System</strong></p>
    '''
    
    html = _get_email_template("❌ โครงการเลยกำหนดส่ง", content_html, "#dc2626")
    return _send_email(to_email, subject, html)


# ---------------------------------------------------------
# 📊 Progress Update Notification (for Admin)
# ---------------------------------------------------------
def send_progress_update_email(to_email, project_name, researcher_name, progress_percent, status):
    """Notify admin when researcher updates progress"""
    subject = f"📊 อัปเดตความคืบหน้า: {project_name[:40]} ({progress_percent}%)"
    
    status_map = {
        'not_started': ('ยังไม่เริ่ม', '#94a3b8'),
        'in_progress': ('กำลังดำเนินการ', '#3b82f6'),
        'completed': ('เสร็จสมบูรณ์', '#10b981'),
        'on_hold': ('หยุดชั่วคราว', '#f59e0b'),
        'delayed': ('ล่าช้า', '#ef4444')
    }
    status_text, status_color = status_map.get(status, ('ไม่ระบุ', '#64748b'))
    
    content_html = f'''
    <p style="color:#475569;line-height:1.6;">มีการอัปเดตความคืบหน้าโครงการ:</p>
    
    <div style="background:#f0fdf4;border-left:4px solid #10b981;padding:16px;margin:16px 0;border-radius:0 8px 8px 0;">
        <p style="margin:0 0 8px 0;color:#1e293b;font-weight:bold;font-size:16px;">📁 {project_name}</p>
        <p style="margin:4px 0;color:#475569;">👤 อัปเดตโดย: <strong>{researcher_name}</strong></p>
        <p style="margin:4px 0;color:#475569;">📈 ความคืบหน้า: <strong style="color:#3b82f6;">{progress_percent}%</strong></p>
        <p style="margin:4px 0;color:#475569;">📋 สถานะ: <span style="color:{status_color};font-weight:bold;">{status_text}</span></p>
    </div>
    '''
    
    html = _get_email_template("📊 อัปเดตความคืบหน้าโครงการ", content_html, "#10b981")
    return _send_email(to_email, subject, html)


# ---------------------------------------------------------
# 🔄 Legacy Function (backward compatibility)
# ---------------------------------------------------------
def send_alert_email(to_email, project_name, days_left):
    """Legacy function for backward compatibility"""
    return send_deadline_reminder(to_email, "ผู้รับผิดชอบโครงการ", project_name, days_left)
