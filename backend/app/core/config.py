from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "TiendAPI Backend"
    api_v1_prefix: str = "/api/v1"

    # development | production — controla verbosidad y detalle de errores.
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://tiendapi:tiendapi@localhost:5432/tiendapi"

    # CORS — orígenes permitidos (coma-separado en la env `CORS_ORIGINS`).
    # `NoDecode` evita que pydantic-settings intente parsear el valor como JSON;
    # el validador de abajo recibe el string crudo y lo separa por comas.
    # Incluye el dev server de Vite y el esquema `tauri://` del empaquetado
    # desktop (ver D-29 en docs/07). Ajustar al dominio real en producción.
    cors_origins: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
    ]

    # Firma del token de sesión/JWT de la autenticación real (fase F1, cierra
    # A-12). En producción debe ser un secreto fuerte vía env, NUNCA el default.
    secret_key: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12 horas

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
