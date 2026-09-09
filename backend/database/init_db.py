import sqlite3
from backend.config import settings
from backend.database.seed_data import (
    SEED_STATIONS,
    SEED_LOADS,
    SEED_ACTIVITIES,
    SEED_USERS,
    SEED_ALERTS
)

def init_database(db_path: str = None):
    target_path = db_path or settings.DB_PATH
    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()

    # 1. Stations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            coordinates TEXT,
            country TEXT,
            battery_capacity_kwh REAL NOT NULL,
            generator_rating_kw REAL NOT NULL,
            base_thermal_rating_kw REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # 2. Weather Records Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temp_c REAL NOT NULL,
            wind_mps REAL NOT NULL,
            lux REAL NOT NULL,
            blizzard_severity REAL NOT NULL
        )
    """)

    # 3. Energy Telemetry Records Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            solar_kw REAL NOT NULL,
            wind_kw REAL NOT NULL,
            gen_kw REAL NOT NULL,
            active_demand_kw REAL NOT NULL,
            battery_soc_pct REAL NOT NULL,
            net_flow_kw REAL NOT NULL,
            mode TEXT NOT NULL
        )
    """)

    # 4. Load Relays Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loads (
            id TEXT PRIMARY KEY,
            station_id TEXT NOT NULL,
            name TEXT NOT NULL,
            priority INT NOT NULL,
            nominal_kw REAL NOT NULL,
            live_kw REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # 5. Scientific Activities Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id TEXT PRIMARY KEY,
            station_id TEXT NOT NULL,
            name TEXT NOT NULL,
            required_kwh REAL NOT NULL,
            duration_hrs REAL NOT NULL,
            deadline_hrs REAL,
            priority INT NOT NULL,
            approval_status TEXT NOT NULL,
            execution_status TEXT NOT NULL,
            recommended_slot TEXT
        )
    """)

    # 6. Alerts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            severity TEXT NOT NULL,
            category TEXT NOT NULL,
            message TEXT NOT NULL,
            root_cause TEXT,
            acknowledged INT DEFAULT 0
        )
    """)

    # 7. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            callsign TEXT,
            station_id TEXT
        )
    """)

    # Seed data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM stations")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", SEED_STATIONS)

    cursor.execute("SELECT COUNT(*) FROM loads")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO loads VALUES (?, ?, ?, ?, ?, ?, ?)", SEED_LOADS)

    cursor.execute("SELECT COUNT(*) FROM activities")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO activities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", SEED_ACTIVITIES)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", SEED_USERS)

    cursor.execute("SELECT COUNT(*) FROM alerts")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO alerts (station_id, severity, category, message, root_cause, acknowledged) VALUES (?, ?, ?, ?, ?, ?)", SEED_ALERTS)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()
    print("Database initialized and seeded successfully.")

