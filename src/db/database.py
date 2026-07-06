import sqlite3
from typing import Generator
import os

DB_NAME = os.environ.get("DB_NAME", default="music.db")

def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id TEXT PRIMARY KEY,
            duration INT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            status TEXT NOT NULL,
            features TEXT
        )
    """)
    conn.commit()
    conn.close()