import uvicorn
from my_app.logger import LOGGING_CONFIG

if __name__ == "__main__":
    uvicorn.run(
        "my_app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=LOGGING_CONFIG
    )