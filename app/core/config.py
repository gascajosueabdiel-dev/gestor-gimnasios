"""Configuración global de la aplicación y variables de entorno."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración global de la aplicación utilizando Pydantic Settings.
    Carga variables de entorno o usa valores predeterminados.
    """
    PROJECT_NAME: str = "Sistema de Gestión de Gimnasios"
    SECRET_KEY: str = "CAMBIAR_ESTA_CLAVE_SECRETA_EN_PRODUCCION_12345678"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    class Config:
        """Configuración adicional para Pydantic Settings."""
        env_file = ".env"


settings = Settings()
