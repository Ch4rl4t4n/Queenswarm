"""Human dashboard login surfaces (password + TOTP + refresh tokens)."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from jose import JWTError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, RootModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import Response

from app.api.deps import DashboardAdmin, DashboardSession, DbSession, JwtSubject
from app.core.config import settings
from app.core.jwt_tokens import (
    create_dashboard_access_token,
    create_pre_2fa_token,
    decode_jwt_optional_typ,
    parse_dashboard_user_subject,
)
from app.core.logging import get_logger
from app.core.redis_client import fetch_dashboard_refresh_user, revoke_dashboard_refresh, store_dashboard_refresh
from app.models.dashboard_api_key import DashboardApiKey
from app.models.dashboard_user import DashboardUser
from app.services.dashboard_api_keys import (
    API_KEY_PREFIX,
    DashboardApiKeyError,
    create_dashboard_api_key,
    list_dashboard_api_keys,
    revoke_dashboard_api_key,
)
from app.services.dashboard_crypto import (
    hash_dashboard_password,
    mint_totp_secret,
    totp_uri_for_email,
    totp_verify,
    verify_dashboard_password,
)

logger = get_logger(__name__)
router = APIRouter(tags=["Auth"])


class _TokenBundle(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class LoginResponse(BaseModel):
    requires_totp: bool
    pre_auth_token: str | None = None
    tokens: _TokenBundle | None = None


class Verify2FARequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    pre_auth_token: str
    totp_code: str = Field(min_length=6, max_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class DashboardUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str | None = None
    is_admin: bool = False
    enable_totp: bool = Field(
        default=True,
        description="When True, provisioning mints ``totp_secret`` so authenticator onboarding is mandatory.",
    )


def _scopes_for(user: DashboardUser) -> str:
    bits = ["dash:read", "dash:operator"]
    if user.is_admin:
        bits.extend(["dash:admin", "dash:recipe_write"])
    return " ".join(sorted(set(bits)))


async def _issue_pair(db_user: DashboardUser) -> dict[str, Any]:
    scopes = _scopes_for(db_user)
    access, ttl = create_dashboard_access_token(
        user_id=db_user.id,
        email=db_user.email,
        scopes=scopes,
    )
    refresh_plain = secrets.token_urlsafe(48)
    ttl_sec = settings.refresh_token_expire_days * 86_400
    await store_dashboard_refresh(refresh_plain, str(db_user.id), ttl_sec)
    logger.info(
        "dashboard_auth.tokens_minted",
        agent_id="dashboard_auth",
        swarm_id="",
        task_id="",
        subject=str(db_user.id),
    )
    return {
        "access_token": access,
        "refresh_token": refresh_plain,
        "expires_in": ttl,
        "token_type": "bearer",
    }


@router.post(
    "/login",
    summary="Authenticate with password (second factor may be required afterward)",
)
async def dashboard_login(body: LoginRequest, db: DbSession) -> LoginResponse:
    stmt = select(DashboardUser).where(DashboardUser.email == body.email.strip().lower())
    try:
        user = await db.scalar(stmt)
    except SQLAlchemyError:
        logger.exception(
            "dashboard_auth.login.lookup_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth persistence unavailable.",
        )

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if not verify_dashboard_password(body.password, user.password_hash):
        logger.warning(
            "dashboard_auth.login.bad_password",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
            email_hash=str(user.email),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if user.totp_required and user.totp_secret:
        pre, _ttl = create_pre_2fa_token(user_id=user.id, email=user.email)
        return LoginResponse(requires_totp=True, pre_auth_token=pre, tokens=None)

    bundle_dict = await _issue_pair(user)
    return LoginResponse(requires_totp=False, tokens=_TokenBundle.model_validate(bundle_dict))


@router.post("/verify-2fa", summary="Finalize login by validating an authenticator code")
async def dashboard_verify_totp(body: Verify2FARequest, db: DbSession) -> _TokenBundle:
    try:
        payload = decode_jwt_optional_typ(body.pre_auth_token.strip())
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid pre-auth token.")

    if payload.get("typ") != "pre_2fa":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a pending 2FA token.")

    sub_raw = payload.get("sub")
    try:
        user_id = uuid.UUID(str(sub_raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupt identity reference.")

    try:
        user = await db.get(DashboardUser, user_id)
    except SQLAlchemyError:
        logger.exception(
            "dashboard_auth.verify.lookup_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")

    if user is None or not user.is_active or user.totp_secret is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticator not provisioned.")

    if not totp_verify(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP.")

    user.totp_verified_at = datetime.now(tz=UTC)
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.verify.persist_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not persist verification.")

    bundle = await _issue_pair(user)
    return _TokenBundle.model_validate(bundle)


@router.post("/refresh", summary="Rotate access token using opaque refresh credential")
async def dashboard_refresh(body: RefreshRequest, db: DbSession) -> _TokenBundle:
    cleaned = body.refresh_token.strip()
    uid_text = await fetch_dashboard_refresh_user(cleaned)
    if uid_text is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh revoked or expired.")
    try:
        user_uuid = uuid.UUID(uid_text)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Corrupt refresh metadata.")

    try:
        user = await db.get(DashboardUser, user_uuid)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive operator.")

    await revoke_dashboard_refresh(cleaned)
    bundle_dict = await _issue_pair(user)
    return _TokenBundle.model_validate(bundle_dict)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke dashboard refresh credential")
async def dashboard_logout(body: LogoutRequest) -> Response:
    await revoke_dashboard_refresh(body.refresh_token.strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)





class MeDetailResponse(BaseModel):
    """Operator envelope consumed by Neon settings screens."""

    email: str
    display_name: str | None = None
    timezone: str | None = None
    notification_prefs: dict[str, Any] = Field(default_factory=dict)
    scopes: list[str]
    is_admin: bool
    totp_required: bool
    totp_has_secret: bool
    totp_verified_at: datetime | None


async def _current_dashboard_user(sess: dict[str, Any], db: DbSession) -> DashboardUser:
    """Load the Postgres row backing the JWT access token."""

    sub = sess.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")
    uid = parse_dashboard_user_subject(sub.strip())
    if uid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed dashboard subject.")
    row = await db.get(DashboardUser, uid)
    if row is None or not row.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard user missing.")
    return row


def _serialize_me(row: DashboardUser) -> MeDetailResponse:
    """Map ORM rows to public profile envelope."""

    return MeDetailResponse(
        email=row.email,
        display_name=row.display_name,
        timezone=row.timezone,
        notification_prefs=dict(row.notification_prefs or {}),
        scopes=sorted(set(_scopes_for(row).split())),
        is_admin=bool(row.is_admin),
        totp_required=bool(row.totp_required),
        totp_has_secret=row.totp_secret is not None,
        totp_verified_at=row.totp_verified_at,
    )


@router.get("/me", summary="Echo dashboard profile + prefs from JWT access tokens")
async def dashboard_me_detail(sess: DashboardSession, db: DbSession) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    return _serialize_me(user)


class ProfilePatchBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    display_name: str | None = Field(default=None, max_length=160)
    timezone: str | None = Field(default=None, max_length=96)


@router.patch("/me/profile", summary="Patch display labels or hive timezone identifiers")
async def dashboard_patch_profile(
    body: ProfilePatchBody,
    sess: DashboardSession,
    db: DbSession,
) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    mutated = False
    if body.display_name is not None:
        trimmed_name = body.display_name.strip()
        user.display_name = trimmed_name[:160] if trimmed_name else None
        mutated = True
    if body.timezone is not None:
        trimmed_tz = body.timezone.strip()
        user.timezone = trimmed_tz[:96] if trimmed_tz else None
        mutated = True
    if not mutated:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one mutable field.",
        )
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.profile_patch_failed",
            agent_id=str(user.id),
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")
    return _serialize_me(user)


class NotificationPrefsPatch(RootModel[dict[str, bool]]):
    """Flattened boolean map merged into ``dashboard_users.notification_prefs``."""


@router.patch("/me/notifications", summary="Merge notification booleans for the cockpit")
async def dashboard_patch_notifications(
    body: NotificationPrefsPatch,
    sess: DashboardSession,
    db: DbSession,
) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    merged = dict(user.notification_prefs or {})
    merged.update(body.root)
    user.notification_prefs = merged
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.notification_prefs_failed",
            agent_id=str(user.id),
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")
    return _serialize_me(user)


class LLMProvidersStatus(BaseModel):
    grok_configured: bool
    anthropic_configured: bool
    openai_configured: bool


@router.get(
    "/integrations/llm-providers",
    summary="Reveal which LiteLLM env keys exist (never return secret payloads)",
)
async def integrations_llm_status(_subject: JwtSubject) -> LLMProvidersStatus:
    def _truthy(value: str | None) -> bool:
        return bool(value and value.strip())

    ok_openai = _truthy(settings.openai_api_key)
    return LLMProvidersStatus(
        grok_configured=_truthy(settings.grok_api_key),
        anthropic_configured=_truthy(settings.anthropic_api_key),
        openai_configured=ok_openai,
    )


class PasswordConfirmBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    password: str = Field(..., min_length=8, max_length=256)


class TotpCodeBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    code: str = Field(..., min_length=6, max_length=12)


class TwoFAProvisionResponse(BaseModel):
    secret_base32: str
    otpauth_uri: str


def _provision_response(user: DashboardUser) -> TwoFAProvisionResponse:
    """Return otpauth provisioning metadata for UX QR rendering."""

    assert user.totp_secret is not None
    uri = totp_uri_for_email(issuer=settings.dashboard_totpissuer, email=user.email, secret=user.totp_secret)
    return TwoFAProvisionResponse(secret_base32=user.totp_secret, otpauth_uri=uri)


@router.post(
    "/profile/totp/provision",
    summary="Mint a fresh TOTP secret after password confirmation",
    response_model=TwoFAProvisionResponse,
)
async def profile_totp_provision(
    body: PasswordConfirmBody,
    sess: DashboardSession,
    db: DbSession,
) -> TwoFAProvisionResponse:
    user = await _current_dashboard_user(sess, db)
    if not verify_dashboard_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    user.totp_secret = mint_totp_secret()
    user.totp_verified_at = None
    user.totp_required = True
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist provisioning material.",
        ) from None
    return _provision_response(user)


@router.post("/profile/totp/confirm", summary="Finalize authenticator enrollment with a numeric OTP")
async def profile_totp_confirm(body: TotpCodeBody, sess: DashboardSession, db: DbSession) -> dict[str, bool]:
    user = await _current_dashboard_user(sess, db)
    if user.totp_secret is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP provisioning has not started.")
    if not totp_verify(user.totp_secret, body.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP.")
    user.totp_verified_at = datetime.now(tz=UTC)
    user.totp_required = True
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    return {"verified": True}


@router.post("/profile/totp/disable", summary="Strip authenticator enrollment after verifying password")
async def profile_totp_disable(body: PasswordConfirmBody, sess: DashboardSession, db: DbSession) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    if not verify_dashboard_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    user.totp_required = False
    user.totp_verified_at = None
    user.totp_secret = None
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    logger.info(
        "dashboard_auth.totp_disabled_self",
        agent_id=str(user.id),
        swarm_id="",
        task_id="",
    )
    return _serialize_me(user)


class ApiKeyCreateBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    label: str | None = Field(default=None, max_length=160)


class ApiKeySummary(BaseModel):
    id: uuid.UUID
    label: str | None
    masked_prefix: str
    created_at: datetime
    revoked_at: datetime | None


class ApiKeyMinted(ApiKeySummary):
    plaintext: str


def _mask_key_row(row: DashboardApiKey) -> ApiKeySummary:
    masked = f"{API_KEY_PREFIX}{row.id.hex[:10]}•••"
    return ApiKeySummary(id=row.id, label=row.label, masked_prefix=masked, created_at=row.created_at, revoked_at=row.revoked_at)


@router.get("/api-keys", summary="List bcrypt-protected scripted credentials tied to this operator")
async def list_dashboard_api_credentials(sess: DashboardSession, db: DbSession) -> list[ApiKeySummary]:
    user = await _current_dashboard_user(sess, db)
    rows = await list_dashboard_api_keys(db, user_id=user.id)
    return [_mask_key_row(row) for row in rows]


@router.post("/api-keys", summary="Create a scripted credential returned once")
async def create_dashboard_api_credential_route(
    body: ApiKeyCreateBody,
    sess: DashboardSession,
    db: DbSession,
) -> ApiKeyMinted:
    user = await _current_dashboard_user(sess, db)
    try:
        row, plaintext = await create_dashboard_api_key(db, user_id=user.id, label=body.label)
        await db.commit()
        await db.refresh(row)
    except DashboardApiKeyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    base = _mask_key_row(row).model_dump()
    return ApiKeyMinted(**base, plaintext=plaintext)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke scripted credential fingerprints",
)
async def revoke_dashboard_api_credential_route(
    key_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
) -> Response:
    user = await _current_dashboard_user(sess, db)
    try:
        await revoke_dashboard_api_key(db, user_id=user.id, key_id=key_id)
        await db.commit()
    except DashboardApiKeyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class _AdminUserMade(BaseModel):
    id: uuid.UUID
    email: str


@router.post(
    "/admin/users",
    response_model=_AdminUserMade,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a dashboard user (requires dash:admin scope)",
)
async def admin_create_dashboard_user(body: DashboardUserCreate, db: DbSession, _: DashboardAdmin) -> _AdminUserMade:
    email_key = body.email.strip().lower()
    exists_stmt = select(DashboardUser.id).where(DashboardUser.email == email_key)

    dup = await db.scalar(exists_stmt)
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already enrolled.")

    totp_secret = mint_totp_secret() if body.enable_totp else None
    entity = DashboardUser(
        email=email_key,
        password_hash=hash_dashboard_password(body.password),
        display_name=body.display_name,
        totp_secret=totp_secret,
        totp_verified_at=None,
        totp_required=bool(body.enable_totp and totp_secret),
        is_admin=body.is_admin,
        is_active=True,
    )
    try:
        db.add(entity)
        await db.flush()
        await db.commit()
        await db.refresh(entity)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.admin_create_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.")

    return _AdminUserMade(id=entity.id, email=entity.email)


@router.post("/2fa/setup", summary="Administrators regenerate TOTP material for their login")
async def setup_totp(sess: DashboardSession, db: DbSession) -> TwoFAProvisionResponse:
    scopes_raw = str(sess.get("scope", ""))
    if "dash:admin" not in scopes_raw.split():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrators only.")
    row = await _current_dashboard_user(sess, db)
    row.totp_secret = mint_totp_secret()
    row.totp_required = True
    await db.commit()
    await db.refresh(row)
    logger.info(
        "dashboard_auth.totp_reprovisioned",
        agent_id=str(row.id),
        swarm_id="",
        task_id="",
        email_hash=row.email,
    )
    return _provision_response(row)


__all__ = ["router"]
