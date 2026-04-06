import sqlite3
from memory.autobiographical import AutobiographicalEntry


class AutobiographicalMemory:
    def __init__(self, db_path="data/memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS autobiographical_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            region TEXT,
            story_theme TEXT,
            active_values TEXT,
            confidence REAL,
            user_feedback TEXT,
            timestamp TEXT
        )
        """)
        self.conn.commit()

    def store(self, entry: AutobiographicalEntry):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO autobiographical_memory
        (user_id, region, story_theme, active_values, confidence, user_feedback, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.user_id,
            entry.region,
            entry.story_theme,
            ",".join(entry.active_values),
            entry.confidence,
            entry.user_feedback,
            entry.timestamp.isoformat()
        ))
        self.conn.commit()

    def fetch_by_region(self, region: str, limit=20):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT story_theme, active_values, confidence
        FROM autobiographical_memory
        WHERE region = ?
        ORDER BY id DESC
        LIMIT ?
        """, (region, limit))
        return cursor.fetchall()
