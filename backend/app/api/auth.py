from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from .deps import get_db
from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)
from ..models.user import User
from ..schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenResponse
from ..schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DB) -> User:
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DB) -> TokenResponse:
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    refresh_token = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(refresh_token)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=refresh_token,
        user=user,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: DB) -> None:
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("kind") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, payload["sub"])
    if user:
        user.refresh_token_hash = None
        db.commit()


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: DB) -> TokenResponse:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise credentials_error

    if payload.get("kind") != "refresh":
        raise credentials_error

    user = db.get(User, payload["sub"])
    if not user or not user.refresh_token_hash:
        raise credentials_error

    if not verify_token(body.refresh_token, user.refresh_token_hash):
        raise credentials_error

    new_refresh = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(new_refresh)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=new_refresh,
        user=user,
    )


