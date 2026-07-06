import os

UPLOAD_DIR = os.environ.get("DB_PATH", default="uploads/songs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DB_NAME = os.environ.get("DB_NAME", default="music.db")

API_KEY_HEADER_NAME = "X-API-Key"
EXPECTED_HASH = os.environ.get("MUSIC_API_KEY_HASH")