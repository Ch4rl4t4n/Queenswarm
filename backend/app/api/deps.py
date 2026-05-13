"""Shared FastAPI dependencies (JWT + database session handles)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.jwt_tokens import decode_jwt_optional_typ, parse_dashboard_user_subject

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



async def require_dashboard_session(
    creds: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Validate dashboard access JWTs minted via ``dashboard_session`` routers."""

    try:
        payload = decode_jwt_optional_typ(creds.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_typ = payload.get("typ") or ""
    if token_typ and token_typ != "dashboard_access":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator access token required.",
        )

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing dashboard subject.",
        )
    if parse_dashboard_user_subject(subject.strip()) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Malformed dashboard identity.",
        )

    return payload


async def require_dashboard_recipe_write(
    sess: dict[str, Any] = Depends(require_dashboard_session),
) -> dict[str, Any]:
    """Require admin dashboard tokens that include the Recipe Library write scope."""

    raw_scope = sess.get("scope")
    if isinstance(raw_scope, str):
        parts = {p for p in raw_scope.split() if p}
    elif isinstance(raw_scope, list):
        parts = {str(p).strip() for p in raw_scope if str(p).strip()}
    else:
        parts = set()
    if "dash:recipe_write" not in parts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin scope dash:recipe_write required to save recipes.",
        )
    return sess


async def dashboard_admin_wall(
    sess: dict[str, Any] = Depends(require_dashboard_session),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Block non-admin dashboards from hitting privileged onboarding routes."""

    from app.models.dashboard_user import DashboardUser

    raw_sub = sess.get("sub")
    if not isinstance(raw_sub, str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dashboard credential missing stable subject.",
        )
    resolved = parse_dashboard_user_subject(raw_sub.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard subject.")

    principal = await db.get(DashboardUser, resolved)
    if principal is None or not principal.is_active or not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scopes required.")

    return True


DashboardSession = Annotated[dict[str, Any], Depends(require_dashboard_session)]
DashboardAdmin = Annotated[bool, Depends(dashboard_admin_wall)]
DashboardRecipeWriter = Annotated[dict[str, Any], Depends(require_dashboard_recipe_write)]
JwtSubject = Annotated[str, Depends(require_subject)]
RecipeMutationSubject = Annotated[str, Depends(require_recipe_catalog_mutation)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
