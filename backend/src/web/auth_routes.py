"""Authentication and administrator user-management endpoints."""
from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import (
    AuthSession, CreateUserRequest, CreateUserResponse, LoginRequest, LoginResponse, PasswordActionInfo,
    PasswordActionRequest, TokenRequest, UpdateUserRequest, User,
    UserResponse, activation_link, authenticate, current_user, create_one_time_token,
    get_db, _hash, _hash_password, _session, require_admin, reset_link, utc_now,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
admin_router = APIRouter(prefix="/admin/users", tags=["user administration"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    return LoginResponse(token=_session(db, user), user=UserResponse.model_validate(user, from_attributes=True))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user


@router.post("/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # The client discards its bearer token; expiring all sessions is unnecessary here.
    return {"status": "ok"}


@router.post("/activate", response_model=UserResponse)
def activate(payload: TokenRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.activation_token_hash == _hash(payload.token), User.activation_expires_at > utc_now()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Lien d’activation invalide ou expiré")
    user.password_hash = _hash_password(payload.password)
    user.activation_token_hash = None
    user.activation_expires_at = None
    db.commit()
    return user


@router.post("/reset-password", response_model=UserResponse)
def reset_password(payload: TokenRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token_hash == _hash(payload.token), User.reset_expires_at > utc_now()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Lien de modification invalide ou expiré")
    user.password_hash = _hash_password(payload.password)
    user.reset_token_hash = None
    user.reset_expires_at = None
    db.commit()
    return user


@router.post("/password-action", response_model=PasswordActionInfo)
def password_action_info(
    payload: PasswordActionRequest,
    db: Session = Depends(get_db),
):
    token_hash = _hash(payload.token)
    if payload.mode == "activation":
        user = db.query(User).filter(User.activation_token_hash == token_hash, User.activation_expires_at > utc_now()).first()
    else:
        user = db.query(User).filter(User.reset_token_hash == token_hash, User.reset_expires_at > utc_now()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
    return PasswordActionInfo(username=user.username)


@admin_router.get("", response_model=list[UserResponse])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.username).all()


@admin_router.post("", response_model=CreateUserResponse)
def create_user(payload: CreateUserRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    username = payload.username.strip()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Ce nom d’utilisateur existe déjà")
    email = payload.email.strip().lower() if payload.email and payload.email.strip() else None
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée")
    raw_token, token_hash, expires_at = create_one_time_token()
    user = User(
        id=secrets.token_hex(16), username=username, email=email,
        group_name=payload.group_name.strip() or None if payload.group_name else None,
        is_admin=payload.is_admin,
        tactical_access=payload.tactical_access or payload.is_admin,
        statsport_access=payload.statsport_access or payload.is_admin,
        activation_token_hash=token_hash, activation_expires_at=expires_at,
    )
    db.add(user)
    db.commit()
    return CreateUserResponse(
        user=UserResponse.model_validate(user, from_attributes=True),
        activation_link=activation_link(raw_token),
    )


@admin_router.post("/{user_id}/reset-link", response_model=dict)
def issue_reset_link(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    raw_token, token_hash, expires_at = create_one_time_token()
    user.reset_token_hash = token_hash
    user.reset_expires_at = expires_at
    db.commit()
    return {"reset_link": reset_link(raw_token)}


@admin_router.post("/{user_id}/activation-link", response_model=dict)
def issue_activation_link(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    raw_token, token_hash, expires_at = create_one_time_token()
    user.activation_token_hash = token_hash
    user.activation_expires_at = expires_at
    user.reset_token_hash = None
    user.reset_expires_at = None
    db.commit()
    return {"activation_link": activation_link(raw_token)}


@admin_router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UpdateUserRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    changes = payload.model_dump(exclude_unset=True)
    if "username" in changes:
        username = (changes["username"] or "").strip()
        if not username:
            raise HTTPException(status_code=422, detail="Le nom d’utilisateur est obligatoire")
        duplicate = db.query(User).filter(User.username == username, User.id != user.id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Ce nom d’utilisateur existe déjà")
        user.username = username
    if "email" in changes:
        email = changes["email"].strip().lower() if changes["email"] and changes["email"].strip() else None
        duplicate = db.query(User).filter(User.email == email, User.id != user.id).first() if email else None
        if duplicate:
            raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée")
        user.email = email
    if "group_name" in changes:
        user.group_name = changes["group_name"].strip() or None if changes["group_name"] else None
    if "tactical_access" in changes:
        user.tactical_access = changes["tactical_access"] or user.is_admin
    if "statsport_access" in changes:
        user.statsport_access = changes["statsport_access"] or user.is_admin
    db.commit()
    db.refresh(user)
    return user
