"""Shared FastAPI dependencies (JWT + database session handles)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

_bearer_scheme = HTTPBearer()


async def require_subject(
    creds: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """Validate Bearer tokens issued with ``settings.secret_key``."""

    try:
        payload = jwt.decode(
            creds.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = payload.get("sub")
    if not isinstance(subject, str) or subject.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim.",
        )
    return subject


JwtSubject = Annotated[str, Depends(require_subject)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
