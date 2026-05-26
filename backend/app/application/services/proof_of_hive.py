"""Proof-of-Hive — HMAC-signed verify receipts for shareable artifact proofs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_activity import list_execution_activity
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

ProofArtifactKind = Literal["publish_pack", "goal", "supervisor_session"]
TrustLane = Literal["auto", "simulate", "live"]

_RECEIPT_VERSION = 1


class ProofReceiptMintOut(BaseModel):
    """Minted verify receipt with share URL."""

    model_config = ConfigDict(extra="ignore")

    token: str
    share_url: str
    artifact_type: ProofArtifactKind
    artifact_id: str
    title: str
    trust_lane: TrustLane
    verified_at: str
    event_kind: str | None = None


class ProofReceiptSummaryOut(BaseModel):
    """Compact receipt row for cockpit."""

    model_config = ConfigDict(extra="ignore")

    token: str
    share_url: str
    title: str
    artifact_type: ProofArtifactKind
    trust_lane: TrustLane
    verified_at: str
    event_kind: str | None = None


class ProofPublicReceiptOut(BaseModel):
    """Public verify view — no tenant secrets."""

    model_config = ConfigDict(extra="ignore")

    valid: bool
    domain: str
    artifact_type: ProofArtifactKind | None = None
    artifact_id: str | None = None
    title: str | None = None
    trust_lane: TrustLane | None = None
    verified_at: str | None = None
    event_kind: str | None = None
    message: str = ""


class ProofOfHiveSnapshotOut(BaseModel):
    """Recent proofs for Operator Cockpit."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    count: int = 0
    receipts: list[ProofReceiptSummaryOut] = Field(default_factory=list)


def _signing_secret() -> bytes:
    raw = (settings.proof_of_hive_signing_secret or settings.secret_key or "").strip()
    return raw.encode("utf-8")


def _base_url() -> str:
    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    return domain if domain.startswith("http") else f"https://{domain}"


def build_proof_share_url(token: str) -> str:
    """Human-friendly public verify page."""

    return f"{_base_url().rstrip('/')}/proof/{token}"


def _encode_body(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_body(body: str) -> dict[str, Any]:
    padded = body + "=" * (-len(body) % 4)
    data = base64.urlsafe_b64decode(padded.encode("ascii"))
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        msg = "Invalid proof payload."
        raise ValueError(msg)
    return parsed


def mint_proof_token(*, payload: dict[str, Any]) -> str:
    """Sign proof payload → URL-safe token ``body.signature``."""

    body = _encode_body(payload)
    digest = hmac.new(_signing_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{digest}"


def verify_proof_token(token: str) -> dict[str, Any] | None:
    """Verify HMAC and decode payload; ``None`` when invalid."""

    trimmed = (token or "").strip()
    if not trimmed or "." not in trimmed:
        return None
    body, signature = trimmed.split(".", 1)
    expected = hmac.new(_signing_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        return _decode_body(body)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _trust_lane_for_publish_kind(kind: str) -> TrustLane:
    if kind in {"social_live", "social_live_auto", "scheduled_live_auto"}:
        return "live"
    if kind in {"queue_approved", "social_simulate", "scheduled_simulate"}:
        return "simulate"
    return "auto"


def mint_publish_proof_receipt(
    *,
    deliverable_id: uuid.UUID,
    title: str,
    kind: str,
    channel: str | None = None,
) -> ProofReceiptMintOut | None:
    """Mint receipt for verified publish-lane event."""

    if not settings.proof_of_hive_enabled:
        return None

    verified_at = datetime.now(tz=UTC).isoformat()
    trust_lane = _trust_lane_for_publish_kind(kind)
    payload = {
        "v": _RECEIPT_VERSION,
        "artifact_type": "publish_pack",
        "artifact_id": str(deliverable_id),
        "title": title[:200],
        "trust_lane": trust_lane,
        "verified_at": verified_at,
        "event_kind": kind,
        "channel": channel,
    }
    token = mint_proof_token(payload=payload)
    return ProofReceiptMintOut(
        token=token,
        share_url=build_proof_share_url(token),
        artifact_type="publish_pack",
        artifact_id=str(deliverable_id),
        title=title[:200],
        trust_lane=trust_lane,
        verified_at=verified_at,
        event_kind=kind,
    )


def verify_proof_public(token: str) -> ProofPublicReceiptOut:
    """Public verify endpoint view."""

    if not settings.proof_of_hive_enabled:
        return ProofPublicReceiptOut(valid=False, domain=_base_url(), message="Proof-of-Hive disabled.")

    payload = verify_proof_token(token)
    if payload is None:
        return ProofPublicReceiptOut(valid=False, domain=_base_url(), message="Invalid or tampered receipt.")

    artifact_type = payload.get("artifact_type")
    trust_lane = payload.get("trust_lane")
    if artifact_type not in {"publish_pack", "goal", "supervisor_session"}:
        return ProofPublicReceiptOut(valid=False, domain=_base_url(), message="Unknown artifact type.")
    if trust_lane not in {"auto", "simulate", "live"}:
        trust_lane = "simulate"

    return ProofPublicReceiptOut(
        valid=True,
        domain=_base_url(),
        artifact_type=artifact_type,  # type: ignore[arg-type]
        artifact_id=str(payload.get("artifact_id") or "") or None,
        title=str(payload.get("title") or "") or None,
        trust_lane=trust_lane,  # type: ignore[arg-type]
        verified_at=str(payload.get("verified_at") or "") or None,
        event_kind=str(payload.get("event_kind") or "") or None,
        message="Queenswarm verify-first receipt — simulation or critic gate passed.",
    )


def compose_recent_proof_receipts(
    tenant: Tenant | None,
    *,
    limit: int = 8,
) -> ProofOfHiveSnapshotOut:
    """Load recent minted receipts from execution studio activity."""

    if not settings.proof_of_hive_enabled:
        return ProofOfHiveSnapshotOut(enabled=False, count=0, receipts=[])

    cap = max(1, min(limit, 20))
    rows = list_execution_activity(tenant, limit=120)
    receipts: list[ProofReceiptSummaryOut] = []
    seen: set[str] = set()

    for row in rows:
        payload = dict(row.get("payload") or {})
        token = str(payload.get("proof_token") or "").strip()
        if not token or token in seen:
            continue
        verified = verify_proof_token(token)
        if verified is None:
            continue
        seen.add(token)
        artifact_type = verified.get("artifact_type")
        trust_lane = verified.get("trust_lane")
        if artifact_type not in {"publish_pack", "goal", "supervisor_session"}:
            continue
        if trust_lane not in {"auto", "simulate", "live"}:
            trust_lane = "simulate"
        receipts.append(
            ProofReceiptSummaryOut(
                token=token,
                share_url=build_proof_share_url(token),
                title=str(verified.get("title") or "Verified artifact")[:200],
                artifact_type=artifact_type,  # type: ignore[arg-type]
                trust_lane=trust_lane,  # type: ignore[arg-type]
                verified_at=str(verified.get("verified_at") or row.get("at") or ""),
                event_kind=str(verified.get("event_kind") or "") or None,
            ),
        )
        if len(receipts) >= cap:
            break

    return ProofOfHiveSnapshotOut(enabled=True, count=len(receipts), receipts=receipts)


async def mint_proof_for_artifact(
    db: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    artifact_type: ProofArtifactKind,
    artifact_id: uuid.UUID,
    event_kind: str = "manual_mint",
) -> ProofReceiptMintOut:
    """Mint receipt for owned artifact (publish pack, goal, or supervisor session)."""

    if not settings.proof_of_hive_enabled:
        msg = "Proof-of-Hive disabled."
        raise ValueError(msg)

    title = "Verified artifact"
    trust_lane: TrustLane = "simulate"

    if artifact_type == "publish_pack":
        from app.domain.outputs.service import fetch_owned_deliverable

        row = await fetch_owned_deliverable(db, deliverable_id=artifact_id, dashboard_user_id=dashboard_user_id)
        if row is None:
            msg = "Publish pack not found."
            raise LookupError(msg)
        from app.application.services.publish_queue import classify_publish_queue_status

        status = classify_publish_queue_status(row)
        if status is None:
            msg = "Deliverable is not a verified publish pack."
            raise ValueError(msg)
        title = str(row.title or "Publish pack")
        trust_lane = "simulate"
    elif artifact_type == "supervisor_session":
        from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

        session = await db.get(SupervisorSession, artifact_id)
        if session is None:
            msg = "Supervisor session not found."
            raise LookupError(msg)
        title = str(session.role or "Supervisor session")[:200]
        trust_lane = "auto"
    elif artifact_type == "goal":
        from app.infrastructure.persistence.models.goal import GoalORM, GoalStatusORM

        goal = await db.get(GoalORM, artifact_id)
        if goal is None or goal.user_id != dashboard_user_id:
            msg = "Goal not found."
            raise LookupError(msg)
        title = str(goal.title or "Queen goal")[:200]
        trust_lane = "auto" if goal.status == GoalStatusORM.COMPLETED else "simulate"
    else:
        msg = "Unsupported artifact type."
        raise ValueError(msg)

    verified_at = datetime.now(tz=UTC).isoformat()
    payload = {
        "v": _RECEIPT_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": str(artifact_id),
        "title": title[:200],
        "trust_lane": trust_lane,
        "verified_at": verified_at,
        "event_kind": event_kind,
    }
    token = mint_proof_token(payload=payload)
    logger.info(
        "proof_of_hive.minted",
        agent_id="proof_of_hive",
        task_id=str(artifact_id),
        artifact_type=artifact_type,
    )
    return ProofReceiptMintOut(
        token=token,
        share_url=build_proof_share_url(token),
        artifact_type=artifact_type,
        artifact_id=str(artifact_id),
        title=title[:200],
        trust_lane=trust_lane,
        verified_at=verified_at,
        event_kind=event_kind,
    )


__all__ = [
    "ProofOfHiveSnapshotOut",
    "ProofPublicReceiptOut",
    "ProofReceiptMintOut",
    "ProofReceiptSummaryOut",
    "build_proof_share_url",
    "compose_recent_proof_receipts",
    "mint_proof_for_artifact",
    "mint_proof_token",
    "mint_publish_proof_receipt",
    "verify_proof_public",
    "verify_proof_token",
]
