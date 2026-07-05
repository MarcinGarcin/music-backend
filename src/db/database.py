import sqlite3

DB_NAME = os.environ.get("DB_NAME", default="music.db")

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS songs (id TEXT PRIMARY KEY, title TEXT, file_path TEXT)"
        )

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()