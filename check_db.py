import sqlite3

def check_system_db():
    print("--- 🔍 START CHECKING ITRACK DATABASE ---")
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # 1. เช็กตารางผู้ใช้งาน (Users)
        print("\n[ Table: users ]")
        users = cur.execute("SELECT id, username, email, role FROM users").fetchall()
        if not users:
            print("⚠️ ไม่มีข้อมูลผู้ใช้งานในระบบ")
        for u in users:
            print(f"ID: {u['id']} | User: {u['username']} | Role: {u['role']} | Email: {u['email']}")

        # 2. เช็กตารางงานวิจัย (Research Projects)
        print("\n[ Table: research_projects ]")
        projects = cur.execute("SELECT * FROM research_projects LIMIT 5").fetchall()
        if not projects:
            print("⚠️ ไม่มีข้อมูลงานวิจัยในระบบ")
        for p in projects:
            print(f"Project: {p['project_th'][:40]}... | By: {p['researcher_name']}")

    except sqlite3.OperationalError as e:
        print(f"❌ Error: {e}")
        print("💡 คำแนะนำ: ลองลบ database.db แล้วรัน app.py เพื่อสร้างตารางใหม่")
    
    conn.close()
    print("\n--- END CHECKING ---")

if __name__ == "__main__":
    check_system_db()