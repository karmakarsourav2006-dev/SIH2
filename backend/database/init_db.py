import sqlite3
from backend.config import settings

DB_PATH = settings.DB_PATH

EQUIPMENT = [
    ("EQ-FREEZER-01", "Medical Vaccine & Blood Freezer", "MEDICAL", "P1", 2.0, 15.0, 0.8, "NORMAL"),
    ("EQ-HEATER-01", "Habitat Primary Glycol Heater", "HEATING", "P1", 8.5, 10.0, 1.0, "NORMAL"),
    ("EQ-WATER-01", "Greywater Recycling Pump Unit", "LIFE_SUPPORT", "P2", 3.2, 20.0, 0.6, "NORMAL"),
    ("EQ-LAB-SPECTRO", "Mass Spectrometer Rig 2", "LAB_EXPERIMENT", "P3", 4.5, 15.0, 0.5, "NORMAL"),
    ("EQ-RAD-RADAR", "Upper Atmosphere Lidar Radar", "LAB_EXPERIMENT", "P3", 6.0, 25.0, 0.4, "NORMAL")
]

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment_signatures (
            device_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            subsystem TEXT NOT NULL,
            priority_tier TEXT NOT NULL,
            nominal_kw REAL NOT NULL,
            tolerance_percent REAL NOT NULL,
            duty_cycle REAL DEFAULT 1.0,
            status TEXT DEFAULT 'NORMAL'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment_telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            observed_kw REAL NOT NULL,
            deviation_percent REAL NOT NULL,
            anomaly_score REAL NOT NULL,
            flagged INTEGER DEFAULT 0,
            diagnosis TEXT,
            FOREIGN KEY(device_id) REFERENCES equipment_signatures(device_id)
        )
    """)

    cursor.executemany("""
        INSERT OR REPLACE INTO equipment_signatures
        (device_id, name, subsystem, priority_tier, nominal_kw,
         tolerance_percent, duty_cycle, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, EQUIPMENT)

    conn.commit()
    conn.close()

    print("Database initialized! 5 equipment signatures registered.")

if __name__ == "__main__":
    init_database()
