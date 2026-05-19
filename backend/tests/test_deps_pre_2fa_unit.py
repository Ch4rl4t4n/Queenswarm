"""JWT dependency guards — pre-2FA tokens must not access hive M2M routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.core.config import settings
from app.presentation.api.deps import require_subject


def _pre_2fa_creds() -> HTTPAuthorizationCredentials:
    user_id = uuid.uuid4()
    expire_at = datetime.now(tz=UTC) + timedelta(minutes=30)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "email": "operator@queenswarm.love",
            "typ": "pre_2fa",
            "exp": int(expire_at.timestamp()),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    raw = token.decode("utf-8") if isinstance(token, bytes) else str(token)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw)


def _m2m_creds() -> HTTPAuthorizationCredentials:
    expire_at = datetime.now(tz=UTC) + timedelta(minutes=15)
    token = jwt.encode(
        {"sub": "hive-ci", "exp": int(expire_at.timestamp())},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    raw = token.decode("utf-8") if isinstance(token, bytes) else str(token)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw)


@pytest.mark.asyncio
async def test_require_subject_rejects_pre_2fa_token() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_subject(_pre_2fa_creds())
    assert exc.value.status_code == 403
    assert "two-factor" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_require_subject_accepts_m2m_token_without_typ() -> None:
    subject = await require_subject(_m2m_creds())
    assert subject == "hive-ci"
