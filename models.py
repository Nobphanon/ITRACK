import sqlite3
import os
import logging
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

DB_NAME = "database.db"

class User(UserMixin):
    """
    User model class for Flask-Login integration.
    """
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

from flask import g

def get_db():
    """
    Establish a connection to the SQLite database.
    Stores connection in Flask g object.
    Returns:
        sqlite3.Connection: Database connection object with Row factory.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """
    Close the database connection if it exists.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initialize the database with required tables (research_projects, users).
    Also creates a default admin user if not exists.
    """
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
            deadline TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'draft'
        )
    """)

    # Check for missing columns (Migration)
    cur = conn.execute("PRAGMA table_info(research_projects)")
    columns = [row['name'] for row in cur.fetchall()]
    
    if 'start_date' not in columns:
        conn.execute("ALTER TABLE research_projects ADD COLUMN start_date TEXT")
    if 'end_date' not in columns:
        conn.execute("ALTER TABLE research_projects ADD COLUMN end_date TEXT")
    if 'status' not in columns:
        conn.execute("ALTER TABLE research_projects ADD COLUMN status TEXT DEFAULT 'draft'")

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

    # ---------- Audit Logs ----------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            details TEXT,
            ip_address TEXT
        )
    """)

    # ---------- Default Admin ----------
    cur = conn.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        # Read password from environment variable (fallback to #123 if not set)
        default_password = os.getenv('DEFAULT_ADMIN_PASSWORD', '#123')
        
        hashed_pw = generate_password_hash(default_password)
        admin_email = os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@itrack.local')
        
        conn.execute("""
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
        """, ("admin", hashed_pw, admin_email, "admin"))
        logger.info(f"✅ Created default admin user with email: {admin_email}")

    conn.commit()

