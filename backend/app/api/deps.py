"""Shared FastAPI dependencies (JWT + database session handles)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

_bearer_scheme = HTTPBearer()


def _payload_has_required_scope(payload: dict[str, Any], required: str) -> bool:
    """Match a single required scope against JWT ``scope`` (string or list)."""

    trimmed = required.strip()
    if not trimmed:
        return True

    raw = payload.get("scope")
    if raw is None:
        return False
    if isinstance(raw, str):
        parts = raw.split()
        return trimmed in parts or raw == trimmed
    if isinstance(raw, list):
        return trimmed in {str(x).strip() for x in raw if str(x).strip()}
    return False


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


async def require_recipe_catalog_mutation(
    creds: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """Reject recipe POST/PATCH/DELETE unless catalog mutations are explicitly enabled and authorized.

    Returns:
        The JWT ``sub`` claim after policy checks.

    Raises:
        HTTPException: 401 on bad tokens, 403 when mutations are disabled or subject not allowed.
    """

    if not settings.recipe_catalog_mutations_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipe catalog mutations are disabled (set RECIPE_CATALOG_MUTATIONS_ENABLED=true).",
        )

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
    trimmed = subject.strip()
    allow = settings.recipe_catalog_mutation_allowlist
    if allow and trimmed not in allow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JWT subject is not authorized to mutate the Recipe Library.",
        )

    req_scope = settings.recipe_catalog_mutation_required_scope
    if req_scope and req_scope.strip():
        if not _payload_has_required_scope(payload, req_scope.strip()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="JWT is missing the required OAuth scope for Recipe Library mutations.",
            )
    return trimmed


JwtSubject = Annotated[str, Depends(require_subject)]
RecipeMutationSubject = Annotated[str, Depends(require_recipe_catalog_mutation)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
