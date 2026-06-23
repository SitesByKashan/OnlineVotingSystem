from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv("backend/.env")


class Settings(BaseSettings):
    app_name: str = "SmartVote API"
    app_version: str = "2.0.0"
    app_secret: str = "change-this-secret-before-demo"
    database_path: str = "smartvote.db"
    frontend_origin: str = "http://localhost:3000"
    access_token_minutes: int = 480
    otp_expiry_minutes: int = 10
    otp_max_attempts: int = 5
    show_dev_otp: bool = False
    firebase_project_id: str | None = None
    firebase_credentials_path: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    model_config = SettingsConfigDict(env_file="backend/.env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
