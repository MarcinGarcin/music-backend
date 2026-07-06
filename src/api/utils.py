import sqlite3
import json
import os
import numpy as np
from sklearn.neighbors import NearestNeighbors
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from src.logger.logger import logger

from src.config import UPLOAD_DIR, DB_NAME
from src.services.recommendation import extract_audio_features


_knn_model = None
_model_version = -1
_cached_ids = []

_executor = ProcessPoolExecutor(max_workers=2)


def process_audio_task(song_id: str, file_path: str):
    conn = sqlite3.connect(DB_NAME)
    try:
        future = _executor.submit(extract_audio_features, file_path)
        try:
            features = future.result(timeout=60)  
        except FutureTimeoutError:
            future.cancel()
            raise RuntimeError("feature extraction timed out")

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE songs SET features = ?, status = ? WHERE id = ?",
            (json.dumps(features), "ready", song_id)
        )
        conn.commit()
    except Exception as e:
        logger.exception(f"[{song_id}] extraction failed")
        conn.execute("UPDATE songs SET status = ? WHERE id = ?", ("error", song_id))
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


def reprocess_songs():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, filename FROM songs WHERE status = 'processing'"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        logger.info("No stuck songs found on startup")
        return

    logger.info(f"Found {len(rows)} stuck song(s), re-queuing...")
    for row in rows:
        file_path = os.path.join(UPLOAD_DIR, row["filename"])
        if not os.path.exists(file_path):
            logger.warning(f"[{row['id']}] file missing on disk, marking as error")
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE songs SET status = 'error' WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            continue

        _executor.submit(process_audio_task, row["id"], file_path)