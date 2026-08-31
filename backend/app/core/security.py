import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

#  Parámetros de Argon2id — configuración **mínima recomendada por OWASP**
#  (Password Storage Cheat Sheet): m=19 MiB, t=2, p=1.
#
#  Se bajan desde el default de `argon2-cffi` (64 MiB, t=3, p=4) por una queja
#  de latencia real en el login, medida antes de tocar nada: el default daba
#  mediana **286 ms y picos de 1683 ms** dentro del contenedor, mientras que
#  esto da 42 ms. El pico venía sobre todo de `parallelism=4` compitiendo por
#  CPU; con p=1 el tiempo además deja de variar.
#
#  ⚠️ **Esto es el piso de lo aceptable, no un punto medio**: bajar más ya sale
#  de la recomendación. Argon2 es lento a propósito — es lo que encarece forzar
#  las contraseñas si alguien se lleva la base, escenario nada teórico acá
#  porque el respaldo del proyecto (D-77) sale **sin cifrar** mientras SQLCipher
#  (D-06) no esté implementado. Si algún día se sube la exigencia, el candidato
#  es la config "estándar" de OWASP (46 MiB, t=1, p=1), medida en 139 ms.
ARGON2_MEMORY_COST_KIB = 19456
ARGON2_TIME_COST = 2
ARGON2_PARALLELISM = 1

_ph = PasswordHasher(
    memory_cost=ARGON2_MEMORY_COST_KIB,
    time_cost=ARGON2_TIME_COST,
    parallelism=ARGON2_PARALLELISM,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """
    ¿El hash guardado usa parámetros distintos a los actuales?

    Hace falta porque **Argon2 guarda sus parámetros dentro del propio hash**:
    un usuario creado con la configuración vieja seguiría verificándose con
    64 MiB/t=3/p=4 para siempre, o sea que seguiría pagando los ~286 ms aunque
    la configuración global ya sea otra. El llamador reescribe el hash tras un
    login correcto — que es el único momento en que la contraseña en claro está
    disponible para volver a derivarlo.
    """
    return _ph.check_needs_rehash(password_hash)


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
