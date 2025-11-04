"""Configuration management for API."""

from dataclasses import dataclass
import os


@dataclass
class Config:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_language: str = os.getenv("WHISPER_LANGUAGE", "pl")

    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "5000"))
    api_debug: bool = os.getenv("API_DEBUG", "False").lower() == "true"

    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/interview_copilot")
    use_database: bool = os.getenv("USE_DATABASE", "False").lower() == "true"

    def validate(self) -> bool:
        ok = True
        if not self.gemini_api_key:
            print("⚠️ GEMINI_API_KEY is missing")
            ok = False
        return ok


config = Config()