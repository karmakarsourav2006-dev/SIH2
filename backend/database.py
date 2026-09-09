import sqlite3
import os
from contextlib import contextmanager
from backend.config import settings
from backend.database.init_db import init_database

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "polar_station.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
def get_db_connection():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # 1. Loads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loads (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                priority INT NOT NULL,
                nominal_kw REAL NOT NULL,
                live_kw REAL NOT NULL,
                status TEXT NOT NULL
            )
        """)
@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

        # 2. Experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                required_kwh REAL NOT NULL,
                duration_hrs REAL NOT NULL,
                priority INT NOT NULL,
                status TEXT NOT NULL
            )
        """)

        # Seed loads if empty
        cursor.execute("SELECT COUNT(*) FROM loads")
        if cursor.fetchone()[0] == 0:
            default_loads = [
                ("L1", "Habitat Life-Support & Thermal Loop", 1, 14.0, 14.2, "ONLINE"),
                ("L2", "Medical Station & Emergency Telemetry", 1, 3.5, 3.4, "ONLINE"),
                ("L3", "Satellite Comms & Emergency Beacon", 1, 2.0, 2.0, "ONLINE"),
                ("L4", "Ice-Core Sub-Surface Thermal Drill", 2, 8.5, 8.6, "ONLINE"),
                ("L5", "Cryogenic Spectrometry Unit", 2, 4.0, 7.6, "ONLINE"),
                ("L6", "Auxiliary Drone Bay & Snow-Rover Recharger", 3, 6.0, 6.0, "ONLINE")
            ]
            cursor.executemany("INSERT INTO loads VALUES (?, ?, ?, ?, ?, ?)", default_loads)

        # Seed experiments if empty
        cursor.execute("SELECT COUNT(*) FROM experiments")
        if cursor.fetchone()[0] == 0:
            default_experiments = [
                ("EXP-01", "Atmospheric Lidar Scan", 18.5, 3.0, 2, "QUEUED"),
                ("EXP-02", "Deep Ice Acoustic Sounding", 32.0, 4.5, 2, "QUEUED"),
                ("EXP-03", "Magnetometer Survey", 12.0, 2.0, 3, "QUEUED")
            ]
            cursor.executemany("INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?)", default_experiments)

        conn.commit()

init_db()

# Auto-initialize database on module import
init_database()
