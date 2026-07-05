from fastapi import FastAPI
from src.api.songs import router as songs_router
from src.db.database import init_db
from src.logger.logger import logger

app = FastAPI(title="Music API")

@app.on_event("startup")
def startup_event():
    logger.info("Starting API and initializing database")
    init_db()

app.include_router(songs_router)
@app.get("/")
async def root():
    return {"message": "Hello World"}