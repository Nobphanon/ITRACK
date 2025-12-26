from flask_mail import Message
from flask import current_app
from extensions import mail
import threading

# ฟังก์ชันสำหรับส่งเมลแบบเงียบๆ (Background Thread)
def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print(f"✅ ส่งอีเมลไปยัง {msg.recipients} สำเร็จ!")
        except Exception as e:
            print(f"❌ ส่งอีเมลล้มเหลว: {e}")

# ✅ นี่คือฟังก์ชันที่ Error หาไม่เจอครับ ต้องมีตัวนี้นะ!
def send_alert_email(to_email, project_name, days_left):
    if not to_email:
        print("⚠️ ไม่พบอีเมลปลายทาง ข้ามการส่ง")
        return False

    subject = f"🔔 แจ้งเตือน: โครงการ '{project_name}' ใกล้ถึงกำหนดส่งแล้ว"
    
    body = f"""
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

    msg = Message(subject=subject, recipients=[to_email])
    msg.html = body

    app = current_app._get_current_object()
    thr = threading.Thread(target=send_async_email, args=(app, msg))
    thr.start()
    
    return True