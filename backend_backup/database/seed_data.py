"""Default seed data for Polar Energy AI platform."""

SEED_STATIONS = [
    ("ST-01", "Maitri Station", "70°45′58″S 11°43′56″E", "India", 160.0, 40.0, 14.0, "ONLINE"),
    ("ST-02", "Bharati Station", "69°24′28″S 76°11′14″E", "India", 200.0, 50.0, 16.0, "ONLINE"),
    ("ST-03", "Amundsen-Scott South Pole", "90°00′00″S 00°00′00″E", "USA", 350.0, 100.0, 28.0, "ONLINE"),
    ("ST-04", "Concordia Station", "75°06′00″S 123°20′00″E", "France/Italy", 220.0, 60.0, 20.0, "ONLINE")
]

SEED_LOADS = [
    ("L1", "ST-01", "Habitat Life-Support & Thermal Loop", 1, 14.0, 14.2, "ONLINE"),
    ("L2", "ST-01", "Medical Station & Emergency Telemetry", 1, 3.5, 3.4, "ONLINE"),
    ("L3", "ST-01", "Satellite Comms & Emergency Beacon", 1, 2.0, 2.0, "ONLINE"),
    ("L4", "ST-01", "Ice-Core Sub-Surface Thermal Drill", 2, 8.5, 8.6, "ONLINE"),
    ("L5", "ST-01", "Cryogenic Spectrometry Unit", 2, 4.0, 7.6, "ONLINE"), # Surging fault anomaly
    ("L6", "ST-01", "Auxiliary Drone Bay & Snow-Rover Recharger", 3, 6.0, 6.0, "ONLINE")
]

SEED_ACTIVITIES = [
    ("ACT-101", "ST-01", "Atmospheric Lidar Aerosol Profiling", 18.5, 3.0, 12.0, 2, "APPROVED", "QUEUED", "14:00 - 17:00 UTC"),
    ("ACT-102", "ST-01", "Deep-Ice Acoustic Glaciological Sounding", 32.0, 4.5, 24.0, 2, "APPROVED", "QUEUED", "Wind Peak Window"),
    ("ACT-103", "ST-01", "Magnetosphere Aurora Spectrometry", 12.0, 2.0, 8.0, 3, "APPROVED", "QUEUED", "Surplus Window"),
    ("ACT-104", "ST-01", "Seismic Bedrock Fracture Sweep", 15.0, 2.5, 18.0, 2, "QUEUED", "QUEUED", "Pending Solar Influx")
]

SEED_USERS = [
    ("USR-01", "Dr. Rajesh Sharma", "COMMANDER", "Polar-Lead", "ST-01"),
    ("USR-02", "Elena Rostova", "RESEARCHER", "Ice-Core-Lead", "ST-01"),
    ("USR-03", "Vikram Patel", "TECHNICIAN", "Grid-Chief", "ST-01"),
    ("USR-04", "Sarah Chen", "RESEARCHER", "Atmospheric-Lead", "ST-01")
]

SEED_ALERTS = [
    ("ST-01", "WARNING", "ANOMALY", "Cryogenic Spectrometry Unit draw elevated (+3.6 kW / +90%).", "Sub-zero compressor valve freeze and cold bearing friction.", 0),
    ("ST-01", "INFO", "SYSTEM", "Polar microgrid operating in Normal Optimization mode.", "Renewable generation baseline nominal.", 1)
]

SEED_EQUIPMENT_SIGNATURES = [
    ("EQ-FREEZER-01", "Medical Vaccine & Blood Freezer", "MEDICAL", "P1", 2.0, 15.0, 0.8, "NORMAL"),
    ("EQ-HEATER-01", "Habitat Primary Glycol Heater", "HEATING", "P1", 8.5, 10.0, 0.8, "NORMAL"),
    ("EQ-WATER-01", "Greywater Recycling Pump Unit", "UTILITIES", "P2", 3.2, 20.0, 0.6, "NORMAL"),
    ("EQ-LAB-SPECTRO", "Mass Spectrometer Rig 2", "LAB_EXPERIMENT", "P3", 4.5, 15.0, 0.5, "NORMAL"),
    ("EQ-RAD-RADAR", "Upper Atmosphere Lidar Radar", "LAB_EXPERIMENT", "P3", 6.0, 25.0, 0.4, "NORMAL"),
]

