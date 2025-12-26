import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"

class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    # ---------- Projects ----------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_th TEXT,
            project_en TEXT,
            researcher_name TEXT,
            researcher_email TEXT,
            affiliation TEXT,
            funding REAL,
            deadline TEXT
        )
    """)

    # ---------- Users ----------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'researcher'
        )
    """)

    # ---------- Default Admin ----------
    cur = conn.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        hashed_pw = generate_password_hash("1234")
        conn.execute("""
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
        """, ("admin", hashed_pw, "admin@test.com", "admin"))

    conn.commit()
    conn.close()
