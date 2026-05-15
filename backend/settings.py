"""Configuración global de la aplicación (Pydantic Settings).

Lee variables desde .env (o entorno). Sin secrets en código.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./var/app.db"
    debounce_ms: int = 1500
    log_level: str = "INFO"


settings = Settings()
