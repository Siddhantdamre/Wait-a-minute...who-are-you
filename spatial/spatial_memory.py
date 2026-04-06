import sqlite3
from datetime import datetime

class SpatialMemory:
    def __init__(self, db_path="data/memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS spatial_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lon REAL,
            region TEXT,
            value_tags TEXT,
            confidence REAL,
            timestamp TEXT
        )
        """)
        self.conn.commit()

    def store(self, lat, lon, region, values, confidence):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO spatial_memory
        (lat, lon, region, value_tags, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            lat,
            lon,
            region,
            ",".join(values),
            confidence,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def fetch_all(self):
        cur = self.conn.cursor()
        cur.execute("SELECT lat, lon, value_tags FROM spatial_memory")
        return cur.fetchall()
