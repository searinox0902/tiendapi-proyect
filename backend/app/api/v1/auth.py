from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_SEATS = 3  # ≤3 asientos por negocio (D-32)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """
    Alta de un negocio nuevo: crea el `Tenant` y su usuario **propietario**.

    MVP: abierto para poder arrancar. En producción este flujo se gatea por el
    proceso de cobro/suscripción (punto abierto A-13).
    """
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    tenant = Tenant(business_name=payload.business_name)
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    #  Migración silenciosa de hashes viejos. Argon2 guarda sus parámetros
    #  dentro del hash, así que una cuenta creada con la configuración anterior
    #  se seguiría verificando con ella —y pagando su latencia— por siempre.
    #  Este es el único punto del sistema donde la contraseña en claro está
    #  disponible para volver a derivar el hash, así que la migración va acá y
    #  no en un script aparte. Va **después** de validar credenciales y estado,
    #  para no reescribir nada de un login que igual va a ser rechazado.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Crea un subusuario (asiento) dentro del negocio del usuario actual."""
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario puede crear usuarios"
        )

    seats = db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == current_user.tenant_id)
    ).scalar_one()
    if seats >= MAX_SEATS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Límite de {MAX_SEATS} asientos alcanzado",
        )

    if db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    role = payload.role if payload.role in ("owner", "member") else "member"
    user = User(
        tenant_id=current_user.tenant_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
