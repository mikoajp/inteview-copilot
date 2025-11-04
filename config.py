"""Configuration management for API."""

from dataclasses import dataclass
import os


@dataclass
class Config:
    # Gemini API Configuration
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")

    # Whisper Configuration
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_language: str = os.getenv("WHISPER_LANGUAGE", "pl")

    # API Server Configuration
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "5000"))
    api_debug: bool = os.getenv("API_DEBUG", "False").lower() == "true"

    # CORS Configuration
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/interview_copilot")
    use_database: bool = os.getenv("USE_DATABASE", "False").lower() == "true"

    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    # Auth Configuration
    require_auth: bool = os.getenv("REQUIRE_AUTH", "True").lower() == "true"

    # Rate Limiting Configuration
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    rate_limit_storage: str = os.getenv("RATE_LIMIT_STORAGE", "memory")  # memory or redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    def validate(self) -> bool:
        """
        Validate configuration settings.

        Returns:
            True if all validations pass, False otherwise
        """
        ok = True

        # Validate Gemini API key
        if not self.gemini_api_key:
            print("⚠️  ERROR: GEMINI_API_KEY is missing")
            ok = False

        # Validate JWT secret in production mode
        if self.require_auth:
            # Check if using default/weak secret
            weak_secrets = [
                "your-secret-key-change-in-production",
                "secret",
                "changeme",
                "test",
                "dev"
            ]

            if self.jwt_secret_key in weak_secrets:
                print("⚠️  ERROR: JWT_SECRET_KEY is using a default/weak value!")
                print("   Please set a strong random secret (minimum 64 characters)")
                print("   Generate one with: openssl rand -hex 32")
                ok = False

            # Check minimum length
            elif len(self.jwt_secret_key) < 32:
                print(f"⚠️  ERROR: JWT_SECRET_KEY is too short ({len(self.jwt_secret_key)} chars)")
                print("   Minimum required: 32 characters for security")
                print("   Recommended: 64+ characters")
                print("   Generate one with: openssl rand -hex 32")
                ok = False

        # Validate database URL in production
        if self.use_database and not self.api_debug:
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                print("⚠️  WARNING: DATABASE_URL points to localhost in production mode")

        return ok


config = Config()
