import sqlite3
from contextlib import contextmanager
from backend.config import settings
from backend.database.init_db import init_database

def get_db_connection():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

__all__ = ["get_db", "get_db_connection", "init_database"]

