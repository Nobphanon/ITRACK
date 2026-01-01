import sqlite3

def check_system_db():
    print("--- 🔍 START CHECKING ITRACK DATABASE ---")
    
    # เชื่อมต่อ Database
    try:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ ไม่สามารถเปิดไฟล์ Database ได้: {e}")
        return

    try:
        # 1. เช็กตารางผู้ใช้งาน (Users)
        print("\n[ 👤 Table: users ]")
        try:
            users = cur.execute("SELECT id, username, email, role FROM users").fetchall()
            if not users:
                print("⚠️ ไม่มีข้อมูลผู้ใช้งานในระบบ")
            for u in users:
                print(f"   - ID: {u['id']} | User: {u['username']} | Role: {u['role']} | Email: {u['email']}")
        except sqlite3.OperationalError:
             print("❌ ไม่พบตาราง 'users' (ลองลบ database.db แล้วรัน app.py ใหม่)")

        # 2. เช็กตารางงานวิจัย (Research Projects)
        print("\n[ 📚 Table: research_projects ]")
        try:
            projects = cur.execute("SELECT * FROM research_projects LIMIT 10").fetchall()
            if not projects:
                print("⚠️ ไม่มีข้อมูลงานวิจัยในระบบ")
            
            for p in projects:
                # ✅ ปรับตรงนี้: ให้โชว์ Email และ Deadline เพื่อเช็คระบบแจ้งเตือน
                project_name = p['project_th'][:30] + "..." if len(p['project_th']) > 30 else p['project_th']
                email = p['researcher_email'] if p['researcher_email'] else "❌ ไม่มีเมล"
                deadline = p['deadline'] if p['deadline'] else "❌ ไม่มีวันส่ง"
                
                print(f"   - Proj: {project_name:<35} | 📧 Mail: {email:<25} | ⏳ Due: {deadline}")
                
        except sqlite3.OperationalError:
            print("❌ ไม่พบตาราง 'research_projects'")

    except Exception as e:
        print(f"❌ Error Unknow: {e}")
    
    conn.close()
    print("\n--- END CHECKING ---")

if __name__ == "__main__":
    check_system_db()