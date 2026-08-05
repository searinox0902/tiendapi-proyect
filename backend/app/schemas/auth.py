import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class RegisterRequest(BaseModel):
    """Bootstrap de un negocio nuevo: crea Tenant + usuario propietario."""

    business_name: str
    full_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Respuesta de login: token + datos del usuario."""
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class UserCreate(BaseModel):
    """Alta de un subusuario (asiento) dentro del negocio actual."""

    full_name: str
    email: EmailStr
    password: str
    role: str = "member"
