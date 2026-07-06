from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api.songs import router as songs_router
from src.api.auth import router as auth_router
from src.db.database import init_db
from src.logger.logger import logger
from src.api.utils import reprocess_songs

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API and initializing database")
    init_db()
    reprocess_songs()
    yield

app = FastAPI(title="Music API", lifespan=lifespan)

app.include_router(songs_router)
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}