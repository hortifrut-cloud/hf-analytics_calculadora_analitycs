"""
Archivo: settings.py
Fecha de modificación: 14/05/2026
Autor: Alex Prieto

Descripción:
Gestor de configuración global de la aplicación utilizando Pydantic Settings. 
Centraliza la lectura de variables de entorno (.env) para el acceso a base 
de datos, niveles de log y parámetros de reactividad.

Acciones Principales:
    - Carga automática de `.env` con codificación UTF-8.
    - Definición de valores por defecto para entornos locales.
    - Validación de tipos para configuraciones críticas.

Estructura Interna:
    - `Settings`: Clase base de configuración.
    - `settings`: Instancia global para importación en el resto del proyecto.
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
