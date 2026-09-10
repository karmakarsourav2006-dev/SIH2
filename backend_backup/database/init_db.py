import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "polar_station.db")

def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 5 Key Polar Station Equipment Signatures
    equipment = [
        ("EQ-FREEZER-01", "Medical Vaccine & Blood Freezer", "MEDICAL", "P1", 2.0, 15.0, 0.8, "NORMAL"),
        ("EQ-HEATER-01", "Habitat Primary Glycol Heater", "HEATING", "P1", 8.5, 10.0, 1.0, "NORMAL"),
        ("EQ-WATER-01", "Greywater Recycling Pump Unit", "LIFE_SUPPORT", "P2", 3.2, 20.0, 0.6, "NORMAL"),
        ("EQ-LAB-SPECTRO", "Mass Spectrometer Rig 2", "LAB_EXPERIMENT", "P3", 4.5, 15.0, 0.5, "NORMAL"),
        ("EQ-RAD-RADAR", "Upper Atmosphere Lidar Radar", "LAB_EXPERIMENT", "P3", 6.0, 25.0, 0.4, "NORMAL")
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO equipment_signatures 
        (device_id, name, subsystem, priority_tier, nominal_kw, tolerance_percent, duty_cycle, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, equipment)

    conn.commit()
    conn.close()
    print("Seed data loaded successfully! 5 equipment signatures registered.")

if __name__ == "__main__":
    seed_data()