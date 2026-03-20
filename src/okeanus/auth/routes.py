"""Authentication API routes — register, login, API key management."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from okeanus.auth.deps import get_current_user, require_role
from okeanus.auth.jwt import (
    create_access_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from okeanus.auth.models import (
    APIKey,
    APIKeyCreate,
    APIKeyListItem,
    APIKeyResponse,
    LoginRequest,
    TokenResponse,
    User,
    UserCreate,
    UserRead,
    UserRole,
)
from okeanus.config import settings
from okeanus.db.postgres import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------


@router.post("/register", response_model=UserRead)
async def register(req: UserCreate) -> UserRead:
    """Register a new user. The first user automatically becomes admin."""
    async with async_session_factory() as session:
        # Check for duplicate email
        existing = (
            await session.execute(select(User).where(User.email == req.email))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        # First user gets admin role
        user_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
        role = UserRole.ADMIN.value if user_count == 0 else UserRole.VIEWER.value

        user = User(
            email=req.email,
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        logger.info("User registered: %s (role=%s)", user.email, user.role)
        return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Authenticate with email/password and receive a JWT."""
    async with async_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == req.email))
        ).scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(str(user.id), user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> UserRead:
    """Get the current authenticated user's profile."""
    return UserRead.model_validate(user)


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    req: APIKeyCreate,
    user: User = Depends(get_current_user),
) -> APIKeyResponse:
    """Create a new API key. The full key is only shown once."""
    full_key, prefix, key_hash = generate_api_key()

    async with async_session_factory() as session:
        ak = APIKey(
            key_hash=key_hash,
            name=req.name,
            prefix=prefix,
            user_id=user.id,
        )
        session.add(ak)
        await session.commit()
        await session.refresh(ak)

        logger.info("API key created: %s... for user %s", prefix, user.email)
        return APIKeyResponse(
            id=ak.id,
            name=ak.name,
            prefix=ak.prefix,
            key=full_key,
            created_at=ak.created_at,
        )


@router.get("/api-keys", response_model=list[APIKeyListItem])
async def list_api_keys(
    user: User = Depends(get_current_user),
) -> list[APIKeyListItem]:
    """List the current user's API keys (prefix only, not full key)."""
    async with async_session_factory() as session:
        keys = (
            await session.execute(
                select(APIKey).where(APIKey.user_id == user.id).order_by(APIKey.created_at.desc())
            )
        ).scalars().all()
    return [APIKeyListItem.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Revoke an API key. Users can only revoke their own keys."""
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID format")

    async with async_session_factory() as session:
        ak = (
            await session.execute(
                select(APIKey).where(APIKey.id == key_uuid, APIKey.user_id == user.id)
            )
        ).scalar_one_or_none()

        if not ak:
            raise HTTPException(status_code=404, detail="API key not found")

        ak.is_active = False
        await session.commit()

    logger.info("API key revoked: %s... by user %s", ak.prefix, user.email)
    return {"detail": "API key revoked"}


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/users",
    response_model=list[UserRead],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_users() -> list[UserRead]:
    """List all users (admin only)."""
    async with async_session_factory() as session:
        users = (
            await session.execute(select(User).order_by(User.created_at.desc()))
        ).scalars().all()
    return [UserRead.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserRead,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_user_role(user_id: str, role: UserRole) -> UserRead:
    """Update a user's role (admin only)."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    async with async_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == uid))
        ).scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.role = role.value
        await session.commit()
        await session.refresh(user)

    logger.info("User %s role updated to %s", user.email, role.value)
    return UserRead.model_validate(user)
