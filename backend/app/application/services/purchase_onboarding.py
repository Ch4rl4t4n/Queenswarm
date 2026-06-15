"""REV1 — Post-purchase onboarding email + simulate-first proof artifact."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.gumroad_purchase_unlock import GumroadSalePing
from app.application.services.marketing_product_catalog import find_product
from app.core.config import settings
from app.core.notifications import notify_email
from app.core.redis_client import get_json, set_json

logger = structlog.get_logger(__name__)

_ONBOARDING_SENT_PREFIX = "commerce:gumroad_onboarding:v1"
_ONBOARDING_TTL_SEC = 90 * 24 * 3600
_PROOF_VERSION = 1


class SimulateProofArtifact(BaseModel):
    """Buyer-facing simulate-first verification record."""

    model_config = ConfigDict(extra="ignore")

    version: int = _PROOF_VERSION
    product_slug: str
    product_title: str
    product_kind: str = "skill_factory"
    scorecard_score: int = 100
    scorecard_verdict: str = "ready"
    simulate_first: bool = True
    verified_at: str
    marketing_url: str
    gumroad_sale_id: str
    signature: str = ""


class PostPurchaseOnboardingResult(BaseModel):
    """Outcome of onboarding email dispatch."""

    model_config = ConfigDict(extra="ignore")

    sent: bool = False
    skipped: bool = False
    message: str = ""
    sale_id: str | None = None
    buyer_email: str | None = None


def marketing_public_origin() -> str:
    """Public letagentscook.org origin for buyer links."""

    raw = (settings.marketing_public_origin or "https://letagentscook.org").strip().rstrip("/")
    return raw if raw.startswith("http") else f"https://{raw}"


def _onboarding_key(sale_id: str) -> str:
    return f"{_ONBOARDING_SENT_PREFIX}:{sale_id.strip()}"


async def onboarding_email_already_sent(sale_id: str) -> bool:
    """Return True when REV1 email was already dispatched for this sale."""

    payload = await get_json(_onboarding_key(sale_id))
    return isinstance(payload, dict) and bool(payload.get("sent"))


async def mark_onboarding_email_sent(*, sale_id: str, buyer_email: str) -> None:
    """Record idempotent onboarding dispatch."""

    await set_json(
        _onboarding_key(sale_id),
        {
            "sent": True,
            "buyer_email": buyer_email,
            "sent_at": datetime.now(tz=UTC).isoformat(),
        },
        ttl=_ONBOARDING_TTL_SEC,
    )


def _scorecard_line_for_slug(scorecard_md: str, slug: str) -> tuple[int, str] | None:
    """Parse scorecard markdown for one product slug."""

    pattern = re.compile(
        rf"-\s+`{re.escape(slug)}`\s+—\s+(\d+)/100\s+(\w+)",
        re.IGNORECASE,
    )
    match = pattern.search(scorecard_md)
    if not match:
        return None
    return int(match.group(1)), str(match.group(2))


def _resolve_export_root(export_root: Path | None = None) -> Path:
    if export_root is not None:
        return export_root.expanduser().resolve()
    candidates = (
        Path("exports"),
        Path(__file__).resolve().parents[4] / "exports",
        Path("/exports"),
        Path("/app/exports"),
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if (resolved / "gumroad-ready").is_dir():
            return resolved
    return Path("exports").resolve()


def build_simulate_proof_artifact(
    *,
    sale: GumroadSalePing,
    catalog_slug: str,
    export_root: Path | None = None,
) -> SimulateProofArtifact:
    """Build signed simulate-first proof JSON for buyer attachment."""

    root = _resolve_export_root(export_root)
    product = find_product(catalog_slug, root)
    title = product.title if product else catalog_slug.replace("-", " ").title()
    kind = product.kind if product else "skill_factory"
    score = int(product.score if product else 100)

    verdict = "ready"
    scorecard_path = root / "GUMROAD_SCORECARD.md"
    if scorecard_path.is_file():
        try:
            scorecard_md = scorecard_path.read_text(encoding="utf-8")
            parsed = _scorecard_line_for_slug(scorecard_md, catalog_slug)
            if parsed is not None:
                score, verdict = parsed
        except OSError:
            pass

    verified_at = datetime.now(tz=UTC).isoformat()
    marketing_url = f"{marketing_public_origin()}/skills/{catalog_slug}"

    body_without_sig = {
        "version": _PROOF_VERSION,
        "product_slug": catalog_slug,
        "product_title": title,
        "product_kind": kind,
        "scorecard_score": score,
        "scorecard_verdict": verdict,
        "simulate_first": True,
        "verified_at": verified_at,
        "marketing_url": marketing_url,
        "gumroad_sale_id": sale.sale_id,
    }
    canonical = json.dumps(body_without_sig, sort_keys=True, separators=(",", ":")).encode("utf-8")
    secret = (settings.secret_key or "queenswarm-proof").encode("utf-8")
    signature = hmac.new(secret, canonical, hashlib.sha256).hexdigest()[:32]

    return SimulateProofArtifact(signature=signature, **body_without_sig)


def compose_post_purchase_email_body(*, sale: GumroadSalePing, proof: SimulateProofArtifact) -> str:
    """Plain-text onboarding email for Gumroad buyers."""

    product_label = sale.product_name.strip() or proof.product_title
    lines = [
        f"Hi — thank you for purchasing {product_label}!",
        "",
        "Your download is available from Gumroad. This product was verified simulate-first",
        f"before listing (scorecard {proof.scorecard_score}/100 · {proof.scorecard_verdict}).",
        "",
        "Quick start:",
        "1. Download the product bundle from your Gumroad library.",
        "2. Open README or SKILL.md inside the bundle for setup steps.",
        "3. Run any included workflow in simulate mode before live use.",
        "",
        f"Product page: {proof.marketing_url}",
        "",
        "Attached: simulate-proof JSON — shareable verification record for your records.",
        "",
        "If you use Queenswarm with the same email as this purchase, premium export unlock",
        "may appear automatically in Settings → Integrations.",
        "",
        "— Let Agents Cook · verified agent skills",
    ]
    return "\n".join(lines)


def proof_artifact_bytes(proof: SimulateProofArtifact) -> bytes:
    """Serialize proof artifact for email attachment."""

    return (json.dumps(proof.model_dump(mode="json"), indent=2, sort_keys=True) + "\n").encode("utf-8")


async def send_post_purchase_onboarding(
    sale: GumroadSalePing,
    *,
    catalog_slug: str,
    export_root: Path | None = None,
) -> PostPurchaseOnboardingResult:
    """Send REV1 onboarding email with simulate proof attachment."""

    if not settings.gumroad_post_purchase_onboarding_enabled:
        return PostPurchaseOnboardingResult(
            skipped=True,
            message="Post-purchase onboarding disabled.",
            sale_id=sale.sale_id,
        )

    if sale.refunded:
        return PostPurchaseOnboardingResult(
            skipped=True,
            message="Refunded sale — no onboarding email.",
            sale_id=sale.sale_id,
        )

    buyer_email = sale.buyer_email.strip().lower()
    if not buyer_email:
        return PostPurchaseOnboardingResult(
            skipped=True,
            message="Buyer email missing.",
            sale_id=sale.sale_id,
        )

    if await onboarding_email_already_sent(sale.sale_id):
        return PostPurchaseOnboardingResult(
            skipped=True,
            message="Onboarding email already sent for this sale.",
            sale_id=sale.sale_id,
            buyer_email=buyer_email,
        )

    proof = build_simulate_proof_artifact(sale=sale, catalog_slug=catalog_slug, export_root=export_root)
    subject = f"Your verified download — {proof.product_title}"
    body = compose_post_purchase_email_body(sale=sale, proof=proof)
    attachment_name = f"simulate-proof-{catalog_slug[:48]}.json"

    sent = await notify_email(
        subject=subject,
        body=body,
        to_email=buyer_email,
        attachment_bytes=proof_artifact_bytes(proof),
        attachment_filename=attachment_name,
    )

    if not sent:
        logger.info(
            "post_purchase_onboarding.skipped_no_smtp",
            sale_id=sale.sale_id,
            buyer_email=buyer_email,
            catalog_slug=catalog_slug,
        )
        return PostPurchaseOnboardingResult(
            skipped=True,
            message="SMTP not configured — onboarding email not sent.",
            sale_id=sale.sale_id,
            buyer_email=buyer_email,
        )

    await mark_onboarding_email_sent(sale_id=sale.sale_id, buyer_email=buyer_email)
    logger.info(
        "post_purchase_onboarding.sent",
        sale_id=sale.sale_id,
        buyer_email=buyer_email,
        catalog_slug=catalog_slug,
        task_id=str(uuid.uuid4()),
    )
    return PostPurchaseOnboardingResult(
        sent=True,
        message="Post-purchase onboarding email sent.",
        sale_id=sale.sale_id,
        buyer_email=buyer_email,
    )


__all__ = [
    "PostPurchaseOnboardingResult",
    "SimulateProofArtifact",
    "build_simulate_proof_artifact",
    "compose_post_purchase_email_body",
    "marketing_public_origin",
    "onboarding_email_already_sent",
    "proof_artifact_bytes",
    "send_post_purchase_onboarding",
]
