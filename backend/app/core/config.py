from pathlib import Path
from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _read_version() -> str:
    """
    Lee `backend/VERSION` — fuente única del versionado semántico del proyecto
    (D-76). Vive dentro de `backend/` y no en la raíz del repo porque el
    `Dockerfile` copia `backend/` completo (`COPY . .` con contexto `backend/`,
    ver `docker-compose.yml`); un archivo en la raíz no llegaría a la imagen
    sin tocar la infra de build. Si el archivo no existe (ej. checkout parcial,
    entorno raro) no se rompe el arranque — se degrada a un valor que se nota
    a simple vista que es un problema, no a una versión real inventada.
    """
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "0.0.0-unknown"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "TiendAPI Backend"
    api_v1_prefix: str = "/api/v1"
    #  Versión de la plataforma (D-76) — distinta de `format_version` de los
    #  archivos de export/import (D-73/D-75): esto identifica QUÉ BUILD generó
    #  el archivo, no la forma/esquema del archivo en sí. Sirve para
    #  diagnosticar compatibilidad ("este archivo lo generó una versión vieja
    #  del backend") sin depender de si el esquema de columnas cambió o no.
    app_version: str = _read_version()

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
