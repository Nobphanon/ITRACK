"""
Database Connection Module for ITrackCDTI
Supports both SQLite (development) and PostgreSQL (production)
"""
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Get DATABASE_URL from environment (Neon PostgreSQL)
DATABASE_URL = os.getenv('DATABASE_URL')

# Detect if we're using PostgreSQL
IS_POSTGRES = DATABASE_URL is not None and 'postgres' in DATABASE_URL


class DatabaseWrapper:
    """
    Wrapper class that provides a consistent interface for both SQLite and PostgreSQL.
    Makes conn.execute(...) work with both databases by adapting placeholders.
    """
    
    def __init__(self, conn, is_postgres=False):
        self._conn = conn
        self._is_postgres = is_postgres
    
    def cursor(self):
        return self._conn.cursor()
    
    def commit(self):
        return self._conn.commit()
    
    def rollback(self):
        return self._conn.rollback()
    
    def close(self):
        return self._conn.close()
    
    def execute(self, query, params=None):
        """
        Execute a query with automatic placeholder adaptation.
        Converts ? to %s for PostgreSQL.
        """
        if self._is_postgres:
            query = query.replace('?', '%s')
        
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor


def get_connection():
    """
    Get database connection based on environment.
    Returns SQLite connection for local dev, PostgreSQL for production.
    Wrapped in DatabaseWrapper for consistent interface.
    """
    if IS_POSTGRES:
        import psycopg2
        import psycopg2.extras
        
        # Fix Render's postgres:// URL if needed
        db_url = DATABASE_URL
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(db_url)
        # Use RealDictCursor for dict-like row access
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        logger.info("✅ Connected to PostgreSQL (Neon)")
        return DatabaseWrapper(conn, is_postgres=True)
    else:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        logger.info("✅ Connected to SQLite (local)")
        return DatabaseWrapper(conn, is_postgres=False)


def get_placeholder():
    """
    Return the correct placeholder for the current database.
    SQLite uses ?, PostgreSQL uses %s
    """
    return '%s' if IS_POSTGRES else '?'


def adapt_query(query):
    """
    Adapt a query for the current database.
    Converts ? placeholders to %s for PostgreSQL.
    """
    if IS_POSTGRES:
        return query.replace('?', '%s')
    return query


def adapt_create_table(query):
    """
    Adapt CREATE TABLE statements for PostgreSQL.
    Converts AUTOINCREMENT to SERIAL.
    """
    if IS_POSTGRES:
        # Replace SQLite AUTOINCREMENT with PostgreSQL SERIAL
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        query = query.replace('integer primary key autoincrement', 'SERIAL PRIMARY KEY')
        # Also handle simple INTEGER PRIMARY KEY (SQLite auto-increments these)
        query = query.replace('INTEGER PRIMARY KEY,', 'SERIAL PRIMARY KEY,')
    return query
