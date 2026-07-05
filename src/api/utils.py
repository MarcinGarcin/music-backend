import sqlite3
import json
import numpy as np
from sklearn.neighbors import NearestNeighbors
from src.services.recommendation import extract_audio_features

_knn_model = None
_model_version = -1
_cached_ids = []


def process_audio_task(song_id: int, file_path: str):
    features = extract_audio_features(file_path)
    
    conn = sqlite3.connect("music_app.db")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE songs SET features = ?, status = ? WHERE id = ?",
            (json.dumps(features.tolist()), "ready", song_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_recommendation_model(db: sqlite3.Connection):
    global _knn_model, _model_version, _cached_ids

    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM songs WHERE status = 'ready'")
    current_db_version = cursor.fetchone()[0]

    if _knn_model is None or current_db_version != _model_version:
        cursor.execute("SELECT id, features FROM songs WHERE status = 'ready'")
        rows = cursor.fetchall()

        if not rows or len(rows) < 5:
            return None, []

        _cached_ids = [row[0] for row in rows]
        cached_features = np.array([json.loads(row[1]) for row in rows])

        _knn_model = NearestNeighbors(n_neighbors=5, algorithm='auto')
        _knn_model.fit(cached_features)
        _model_version = current_db_version

    return _knn_model, _cached_ids