"""FastAPI dependency injection for authentication."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from okeanus.auth.jwt import decode_access_token, hash_api_key
from okeanus.auth.models import APIKey, User, UserRole
from okeanus.db.postgres import async_session_factory

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Security(api_key_header),
) -> User:
    """Authenticate via JWT Bearer token OR X-API-Key header.

    Tries JWT first, then falls back to API key.
    """
    if credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = payload["sub"]
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        async with async_session_factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user

    if api_key:
        key_hash = hash_api_key(api_key)
        async with async_session_factory() as session:
            ak = (
                await session.execute(
                    select(APIKey).where(
                        APIKey.key_hash == key_hash,
                        APIKey.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()

            if not ak:
                raise HTTPException(status_code=401, detail="Invalid API key")

            # Update last_used timestamp
            ak.last_used_at = datetime.now(timezone.utc)
            await session.commit()

            user = (
                await session.execute(select(User).where(User.id == ak.user_id))
            ).scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Bearer token or X-API-Key header.",
    )


def require_role(*roles: UserRole):
    """Dependency factory: require user has one of the specified roles."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {', '.join(r.value for r in roles)}",
            )
        return user

    return _check
