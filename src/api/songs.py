import os
import shutil
import sqlite3
import json
import uuid
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.db.database import get_db
from src.services.yt_service import YouTubeSearchService
from src.api.auth import verify_api_key
from src.services.recommendation import get_knn_recommendations, extract_audio_features
from src.api.utils import process_audio_task, get_recommendation_model
from src.config import UPLOAD_DIR


router = APIRouter(
    prefix="/songs", 
    tags=["songs"],
    dependencies=[Depends(verify_api_key)]
)

yt_service = YouTubeSearchService()

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg": ".mp3"
}

class SongUpdate(BaseModel):
    title: str

@router.get("/search/")
def search_youtube(query: str, limit: int = 5):
    try:
        results = yt_service.search_songs(query, limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def upload_song(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    duration: int = Form(...),
    youtube_id: str = Form(...),
    db: sqlite3.Connection = Depends(get_db),
):
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Invalid audio format")

    file_location = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO songs
            (
                id,
                title,
                filename,
                duration,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                youtube_id,
                title,
                file.filename,
                duration,
                "processing"
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Song with this ID already exists")

    background_tasks.add_task(process_audio_task, youtube_id, file_location)

    return {
        "message": "Upload started",
        "song_id": youtube_id,
    }

@router.get("/")
def get_songs(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, title, duration FROM songs")
    return [dict(row) for row in cursor.fetchall()]

@router.get("/{song_id}")
def get_song(song_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT filename FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()
        
    if not row:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Not found",
                "job": "download_and_upload",
                "youtube_id": song_id
            }
        )
        
    file_path = os.path.join(UPLOAD_DIR, row["filename"])
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "File missing from disk",
                "job": "download_and_upload",
                "youtube_id": song_id
            }
        )

    return FileResponse(file_path, filename=row["filename"])

@router.delete("/{song_id}")
def delete_song(song_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT filename FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
            
    cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
    db.commit()
        
    file_path = os.path.join(UPLOAD_DIR, row["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
        
    return {"message": "Deleted"}

@router.get("/recommendations/{song_id}")
def get_recommendations(song_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT features FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()

    if not row or not row["features"]:
        raise HTTPException(status_code=404, detail="Song or features not found")

    target_features = np.array([json.loads(row["features"])])

    model, song_ids = get_recommendation_model(db)

    if model is None:
        return {"recommendations": []}

    distances, indices = model.kneighbors(target_features)

    recommendations = []
    for idx in indices[0]:
        rec_id = song_ids[idx]
        if rec_id != song_id:
            recommendations.append(rec_id)

    return {"recommendations": recommendations}