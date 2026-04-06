import sqlite3
from datetime import datetime
from memory.schemas import MemoryEntry


class LongTermMemory:
    def __init__(self, db_path="data/memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            system_output TEXT,
            timestamp TEXT,
            region TEXT,
            theme TEXT,
            modality TEXT
        )
        """)
        self.conn.commit()

    def store(self, memory: MemoryEntry):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO memories (user_input, system_output, timestamp, region, theme, modality)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            memory.user_input,
            memory.system_output,
            memory.timestamp.isoformat(),
            memory.region,
            memory.theme,
            memory.modality
        ))
        self.conn.commit()

    def fetch_recent(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT user_input, system_output, timestamp, region, theme, modality
        FROM memories
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        return cursor.fetchall()
