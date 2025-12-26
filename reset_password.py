from werkzeug.security import generate_password_hash
import sqlite3
import getpass # ใช้ซ่อนรหัสผ่านตอนพิมพ์ (เหมือนตู้ ATM)

def reset_password():
    print("=== ระบบรีเซ็ตรหัสผ่าน Admin ===")
    
    # 1. รับค่าจากคีย์บอร์ด
    target_user = input("ระบุชื่อผู้ใช้ (Default: admin): ").strip() or "admin"
    
    # ใช้ getpass เพื่อไม่ให้เห็นตัวหนังสือตอนพิมพ์ (เพื่อความปลอดภัย)
    # หรือถ้าอยากเห็นตัวเลขก็ใช้ input() ธรรมดาได้ครับ
    new_pass = input(f"กรอกรหัสผ่านใหม่สำหรับ '{target_user}': ").strip()
    
    if not new_pass:
        print("❌ ยกเลิก: คุณไม่ได้กรอกรหัสผ่าน")
        return

    # 2. แปลงรหัสเป็น Hash
    hashed_pw = generate_password_hash(new_pass)
    
    # 3. บันทึกลงฐานข้อมูล
    conn = sqlite3.connect("database.db")
    try:
        cur = conn.cursor()
        # เช็คก่อนว่ามี User นี้ไหม
        cur.execute("SELECT id FROM users WHERE username = ?", (target_user,))
        if not cur.fetchone():
            print(f"❌ ไม่พบผู้ใช้ชื่อ '{target_user}' ในระบบ")
            return

        cur.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_pw, target_user))
        conn.commit()
        print(f"\n✅ สำเร็จ! เปลี่ยนรหัสผ่านของ '{target_user}' เรียบร้อยแล้ว")
        print(f"👉 รหัสผ่านใหม่คือ: {new_pass}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_password()