import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    PROJECT_NAME: str = "Galvão Logi"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./galvao_logi.db")
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

settings = Settings()
