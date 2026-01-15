import os
import logging
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from flask import g

# Import database utilities
from database import get_connection, adapt_query, adapt_create_table, IS_POSTGRES

logger = logging.getLogger(__name__)


class User(UserMixin):
    """
    User model class for Flask-Login integration.
    """
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role


def get_db():
    """
    Establish a connection to the database.
    Stores connection in Flask g object.
    Returns: Database connection object.
    """
    if 'db' not in g:
        g.db = get_connection()
    return g.db


def close_db(e=None):
    """
    Close the database connection if it exists.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def execute_query(conn, query, params=None):
    """
    Execute a query with automatic placeholder adaptation.
    """
    adapted_query = adapt_query(query)
    cursor = conn.cursor()
    if params:
        cursor.execute(adapted_query, params)
    else:
        cursor.execute(adapted_query)
    return cursor


def init_db():
    """
    Initialize the database with required tables (research_projects, users).
    Also creates default users if not exist.
    Supports both SQLite and PostgreSQL.
    """
    conn = get_db()
    cursor = conn.cursor()

    # ---------- Projects ----------
    if IS_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_projects (
                id SERIAL PRIMARY KEY,
                project_th TEXT,
                project_en TEXT,
                researcher_name TEXT,
                researcher_email TEXT,
                affiliation TEXT,
                funding REAL,
                deadline TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'draft',
                progress_percent INTEGER DEFAULT 0,
                current_status TEXT DEFAULT 'not_started',
                last_updated_at TEXT,
                last_updated_by INTEGER,
                assigned_researcher_id INTEGER
            )
        """)
    else:
        cursor.execute("""
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
                status TEXT DEFAULT 'draft',
                progress_percent INTEGER DEFAULT 0,
                current_status TEXT DEFAULT 'not_started',
                last_updated_at TEXT,
                last_updated_by INTEGER,
                assigned_researcher_id INTEGER
            )
        """)

    # ---------- Users ----------
    if IS_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'researcher'
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'researcher'
            )
        """)

    # ---------- Audit Logs ----------
    if IS_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
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
    else:
        cursor.execute("""
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

    # ---------- Project Updates History ----------
    if IS_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_updates (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                updated_by INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                progress_percent INTEGER NOT NULL,
                status TEXT NOT NULL,
                remarks TEXT,
                delay_reason TEXT,
                FOREIGN KEY (project_id) REFERENCES research_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                updated_by INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                progress_percent INTEGER NOT NULL,
                status TEXT NOT NULL,
                remarks TEXT,
                delay_reason TEXT,
                FOREIGN KEY (project_id) REFERENCES research_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
    logger.info("✅ All tables ready")

    # ---------- Default Admin ----------
    placeholder = '%s' if IS_POSTGRES else '?'
    cursor.execute(f"SELECT * FROM users WHERE username = {placeholder}", ('admin',))
    if not cursor.fetchone():
        default_password = os.getenv('DEFAULT_ADMIN_PASSWORD', '#123')
        hashed_pw = generate_password_hash(default_password)
        admin_email = os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@itrack.local')
        
        cursor.execute(f"""
            INSERT INTO users (username, password, email, role)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, ("admin", hashed_pw, admin_email, "admin"))
        logger.info(f"✅ Created default admin user with email: {admin_email}")

    # ---------- Default Manager ----------
    cursor.execute(f"SELECT * FROM users WHERE username = {placeholder}", ('manager',))
    if not cursor.fetchone():
        default_password = os.getenv('DEFAULT_MANAGER_PASSWORD', '#123')
        hashed_pw = generate_password_hash(default_password)
        manager_email = 'manager@itrack.local'
        
        cursor.execute(f"""
            INSERT INTO users (username, password, email, role)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, ("manager", hashed_pw, manager_email, "manager"))
        logger.info(f"✅ Created default manager user with email: {manager_email}")

    # ---------- Default Researcher ----------
    cursor.execute(f"SELECT * FROM users WHERE username = {placeholder}", ('researcher',))
    if not cursor.fetchone():
        default_password = os.getenv('DEFAULT_RESEARCHER_PASSWORD', '#123')
        hashed_pw = generate_password_hash(default_password)
        researcher_email = 'researcher@itrack.local'
        
        cursor.execute(f"""
            INSERT INTO users (username, password, email, role)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, ("researcher", hashed_pw, researcher_email, "researcher"))
        logger.info(f"✅ Created default researcher user with email: {researcher_email}")

    conn.commit()
