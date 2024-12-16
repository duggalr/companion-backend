from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):  # will load the .env file
    openai_key: str
    redis_backend_url: str
    db_user: str
    db_password: str
    db_name: str
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "https://staging.companionai.dev",
        "https://www.companionai.dev"
    ]

    class Config:
        env_file = ".env"

settings = Settings()