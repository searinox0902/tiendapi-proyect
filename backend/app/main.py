import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import check_database_connection
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("tiendapi")

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:8]
    logger.info("→ %s %s [%s]", request.method, request.url.path, request_id)
    response = await call_next(request)
    logger.info(
        "← %s %s %s [%s]",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # HTTPException y errores de validación se manejan con los handlers propios
    # de FastAPI; esto solo captura fallos no previstos y evita filtrar el
    # traceback al cliente. El detalle completo queda en el log del servidor.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    db_ok = check_database_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "environment": settings.environment,
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
