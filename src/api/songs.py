import os
import shutil
import sqlite3
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.db.database import get_db

router = APIRouter(prefix="/songs", tags=["songs"])

UPLOAD_DIR = os.environ.get("DB_PATH", default="uploads/songs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class SongUpdate(BaseModel):
    title: str

@router.post("/")
def create_song(song_id: str = Form(...), title: str = Form(...), file: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO songs (id, title, file_path) VALUES (?, ?, ?)", (song_id, title, file_path))
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Song with this YouTube ID already exists")
        
    return {"id": song_id, "title": title, "file_path": file_path}

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