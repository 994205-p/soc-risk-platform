"""
Central configuration. All secrets/config come from environment variables
(.env for local dev) -- nothing is hardcoded, per project security requirements.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Default falls back to a local SQLite file so the project runs with zero
    # external services for a quick demo. docker-compose.yml overrides this
    # with a real Postgres DATABASE_URL for the "full stack" path.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./soc_risk.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    ALGORITHM: str = "HS256"

    # Optional LLM explanation layer -- application MUST work without this.
    ENABLE_LLM_EXPLANATIONS: bool = os.getenv("ENABLE_LLM_EXPLANATIONS", "false").lower() == "true"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Data freshness thresholds (hours) used by the risk engine / UI badges.
    FRESH_THRESHOLD_HOURS: int = int(os.getenv("FRESH_THRESHOLD_HOURS", "24"))
    AGING_THRESHOLD_HOURS: int = int(os.getenv("AGING_THRESHOLD_HOURS", "72"))
    # Beyond AGING_THRESHOLD_HOURS -> STALE

    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    class Config:
        env_file = ".env"


settings = Settings()
