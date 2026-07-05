import os
import shutil
import sqlite3
import json
import uuid
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.db.database import get_db
from src.services.yt_service import YouTubeSearchService
from src.api.auth import verify_api_key
from src.services.recommendation import get_knn_recommendations, extract_audio_features
from src.api.utils import process_audio_task, get_recommendation_model

router = APIRouter(
    prefix="/songs", 
    tags=["songs"],
    dependencies=[Depends(verify_api_key)]
)

UPLOAD_DIR = os.environ.get("DB_PATH", default="uploads/songs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    db: sqlite3.Connection = Depends(get_db)
):
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Invalid audio format")

    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO songs (filename, status) VALUES (?, ?)", 
        (file.filename, "processing")
    )
    song_id = cursor.lastrowid
    db.commit()

    background_tasks.add_task(process_audio_task, song_id, file_location)

    return {"message": "Upload started", "song_id": song_id}

@router.get("/")
def get_songs(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM songs")
    return [dict(row) for row in cursor.fetchall()]

@router.get("/{song_id}")
def get_song(song_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
        
    return FileResponse(row["file_path"], filename=os.path.basename(row["file_path"]))

@router.put("/{song_id}")
def update_song(song_id: str, song_update: SongUpdate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE songs SET title = ? WHERE id = ?", (song_update.title, song_id))
    db.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
            
    return {"id": song_id, "title": song_update.title}

@router.delete("/{song_id}")
def delete_song(song_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT file_path FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
            
    cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
    db.commit()
        
    file_path = row["file_path"]
    if os.path.exists(file_path):
        os.remove(file_path)
        
    return {"message": "Deleted"}

@router.get("/recommendations/{song_id}")
def get_recommendations(song_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT features FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Song not found")

    target_features = np.array([json.loads(row[0])])

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