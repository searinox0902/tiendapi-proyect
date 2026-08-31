import uuid
from typing import Callable, Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.images import resolve_image_url
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resuelve el usuario autenticado a partir del token Bearer (JWT)."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except Exception:  # token inválido, expirado o malformado
        raise unauthorized

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def get_tenant_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    """
    Deriva el `tenant_id` del token de sesión firmado — **cierra A-12**.

    Antes era un stub que confiaba en el header `X-Tenant-ID` enviado por el
    cliente; ahora el tenant viaja dentro del JWT (docs/04 §3, D-08) y no es
    falsificable sin la clave del servidor.
    """
    return current_user.tenant_id


#  `(sku, url_guardada) -> url_a_mostrar`. Se tipa para que los routers no
#  tengan que importar `Callable[...]` cada uno por su lado.
ImageResolver = Callable[[str, Optional[str]], Optional[str]]


def get_image_resolver(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ImageResolver:
    """
    Resolvedor de imagen de Referencia ya atado a este tenant y a este request (D-84).

    Existe como dependencia y no como llamada suelta por el `base_url`: la URL
    local se arma con el host de **este** request, así que los siete puntos que
    emiten `image_url` necesitan el `Request` a mano. Inyectarlo una vez acá
    evita que cada endpoint tenga que recibirlo y recordar de dónde sacar la base.
    """
    base_url = str(request.base_url)

    def resolve(sku: str, stored_url: Optional[str]) -> Optional[str]:
        return resolve_image_url(sku, stored_url, tenant_id, base_url)

    return resolve
