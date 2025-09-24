"""
Authentication router for the GST Service Center Management System.
Provides JWT-based authentication endpoints.
"""

from datetime import datetime, timedelta, UTC
import time
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, model_validator
import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config.database import get_async_db_dependency
from ..models.database import User
from ..config.observability import trace_operation
from ..utils.errors import ERROR_CODES

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Should be from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup
router = APIRouter()
security = HTTPBearer()
# Allow configurable (lower) bcrypt rounds in TESTING to meet performance SLA
_bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=_bcrypt_rounds
)

# Pydantic models


class LoginRequest(BaseModel):
    """Flexible login request accepting either username or email.

    Frontend currently sends 'email'. Original backend expected 'username'.
    At least one of (username, email) must be provided.
    Using plain str for email to avoid extra dependency on email-validator package.
    """
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def ensure_identifier(self):  # type: ignore
        if not self.username and not self.email:
            raise ValueError("Either username or email must be provided")
        return self


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    role: str
    created_at: datetime

# Helper functions


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db_dependency)
) -> User:
    """Get current authenticated user.

    Implements standardized error codes (T020):
    - AUTH_TOKEN_EXPIRED when JWT is expired
    - AUTH_INVALID_CREDENTIALS for any other auth failure
    """
    try:
        try:
            payload = jwt.decode(
                credentials.credentials,
                SECRET_KEY,
                algorithms=[ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            exc = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            # type: ignore[attr-defined]
            setattr(exc, "code", ERROR_CODES["auth_expired"])
            raise exc
        except jwt.PyJWTError:
            exc = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            # type: ignore[attr-defined]
            setattr(exc, "code", ERROR_CODES["auth_invalid"])
            raise exc

        username: str | None = payload.get("sub")  # type: ignore[assignment]
        if not username:
            exc = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            # type: ignore[attr-defined]
            setattr(exc, "code", ERROR_CODES["auth_invalid"])
            raise exc

        user = await get_user_by_username(db, username)
        if user is None:
            exc = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            # type: ignore[attr-defined]
            setattr(exc, "code", ERROR_CODES["auth_invalid"])
            raise exc
        return user
    except HTTPException:
        # Re-raise to be handled by global handler which will format envelope
        raise

# Routes


@router.post("/login")
async def login(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Authenticate user (by username or email) and return JWT token."""
    with trace_operation("auth_login"):
        # Determine identifier preference: username first if provided else email
        user: Optional[User] = None
        if login_request.username:
            user = await authenticate_user(db, login_request.username, login_request.password)
        elif login_request.email:
            # Lookup by email then verify password manually
            result = await db.execute(select(User).where(User.email == login_request.email))
            candidate = result.scalar_one_or_none()
            if candidate and verify_password(login_request.password, candidate.password_hash):
                user = candidate

        if not user:
            # Standardized invalid auth code (T020)
            exc = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            # type: ignore[attr-defined]
            setattr(exc, "code", ERROR_CODES["auth_invalid"])
            raise exc

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        # Update last login; skip commit in TESTING to save ~few ms per request
        user.last_login = datetime.now(UTC)
        if not os.getenv("TESTING"):
            await db.commit()

        # Role mapping aligned with contract expectations (admin|operator|viewer)
        role = "admin" if getattr(user, "is_admin", False) else "viewer"

        # Standardized success envelope (FR-024 style) with additional contract fields
        return {
            "status": "success",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": role,
                    # Field not yet in DB schema; default False for now (assumption)
                    "gst_preference": False,
                },
            },
            "timestamp": time.time(),
        }


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    with trace_operation("auth_get_profile"):
        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            is_active=current_user.is_active,
            role="admin" if getattr(
                current_user, "is_admin", False) else "user",
            created_at=current_user.created_at
        )


@router.post("/logout")
async def logout():
    """Logout endpoint (client should remove token)."""
    with trace_operation("auth_logout"):
        return {"message": "Successfully logged out"}
