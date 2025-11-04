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

    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    # Auth Configuration
    require_auth: bool = os.getenv("REQUIRE_AUTH", "True").lower() == "true"

    def validate(self) -> bool:
        ok = True
        if not self.gemini_api_key:
            print("⚠️ GEMINI_API_KEY is missing")
            ok = False
        return ok


config = Config()