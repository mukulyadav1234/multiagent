from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    MAX_AGENT_RETRIES: int = 2
    OUTPUT_DIR: str = "outputs"
    SSL_VERIFY: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
