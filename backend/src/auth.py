"""Authentication, user permissions, and one-time account tokens."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import Session

from .SportsDynamics.models.base import Base, TimestampMixin
from .config.database import engine, get_db
from .config.settings import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(254), unique=True, nullable=True)
    group_name = Column(String(120), nullable=True)
    password_hash = Column(String(255), nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    tactical_access = Column(Boolean, nullable=False, default=False)
    statsport_access = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    activation_token_hash = Column(String(64), nullable=True)
    activation_expires_at = Column(DateTime(timezone=True), nullable=True)
    reset_token_hash = Column(String(64), nullable=True)
    reset_expires_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def password_configured(self) -> bool:
        return bool(self.password_hash)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


def ensure_auth_tables() -> None:
    """Create only the auth tables when an older database is not fully migrated."""
    User.__table__.create(bind=engine, checkfirst=True)
    AuthSession.__table__.create(bind=engine, checkfirst=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class TokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class PasswordActionInfo(BaseModel):
    username: str


class PasswordActionRequest(BaseModel):
    mode: Literal["activation", "reset"]
    token: str = Field(min_length=20, max_length=256)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    group_name: str | None = Field(default=None, max_length=120)
    tactical_access: bool = False
    statsport_access: bool = False
    is_admin: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, separator, domain = normalized.partition("@")
        if not separator or not local or "." not in domain or any(char.isspace() for char in normalized):
            raise ValueError("Adresse e-mail invalide")
        return normalized


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=254)
    group_name: str | None = Field(default=None, max_length=120)
    tactical_access: bool | None = None
    statsport_access: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str | None
    group_name: str | None
    is_admin: bool
    tactical_access: bool
    statsport_access: bool
    is_active: bool
    password_configured: bool


class CreateUserResponse(BaseModel):
    user: UserResponse
    activation_link: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


bearer = HTTPBearer(auto_error=False)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or not encoded.startswith("scrypt$"):
        return False
    _, salt_hex, digest_hex = encoded.split("$", 2)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        group_name=user.group_name,
        is_admin=user.is_admin,
        tactical_access=user.tactical_access,
        statsport_access=user.statsport_access,
        is_active=user.is_active,
        password_configured=user.password_configured,
    )


def _session(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    db.add(AuthSession(id=secrets.token_hex(16), user_id=user.id, token_hash=_hash(raw_token), expires_at=utc_now() + timedelta(days=settings.auth_session_days)))
    db.commit()
    return raw_token


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not user.is_active or not _verify_password(password, user.password_hash):
        return None
    return user


def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db: Annotated[Session, Depends(get_db)]) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
    session = db.query(AuthSession).filter(AuthSession.token_hash == _hash(credentials.credentials)).first()
    if not session or session.expires_at <= utc_now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expirée")
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur indisponible")
    return user


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès administrateur requis")
    return user


def require_tactical_access(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_admin and not user.tactical_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès TacticalData refusé")
    return user


def require_statsport_access(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_admin and not user.statsport_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès STATSport refusé")
    return user


def create_one_time_token() -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    return raw_token, _hash(raw_token), utc_now() + timedelta(hours=settings.auth_token_hours)


def activation_link(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/activate?token={token}"


def reset_link(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
