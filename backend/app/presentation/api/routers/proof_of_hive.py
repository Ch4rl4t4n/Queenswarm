"""Public Proof-of-Hive verify endpoints."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.proof_of_hive import (
    ProofPublicReceiptOut,
    compose_recent_proof_receipts,
    mint_proof_for_artifact,
    verify_proof_public,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/operator/proof", tags=["Proof-of-Hive"])
public_router = APIRouter(prefix="/public/proof", tags=["Public"])


class ProofMintRequest(BaseModel):
    """Mint shareable verify receipt for owned artifact."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: Literal["publish_pack", "goal", "supervisor_session"]
    artifact_id: uuid.UUID


def _require_owner_or_admin(principal: dict) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@public_router.get(
    "/{proof_token}",
    response_model=ProofPublicReceiptOut,
    summary="Verify Proof-of-Hive receipt (public, no auth)",
)
async def verify_public_proof(proof_token: str) -> ProofPublicReceiptOut:
    """Return tamper-evident verify receipt for external sharing."""

    return verify_proof_public(proof_token)


@router.get("/recent", summary="Recent Proof-of-Hive receipts for tenant")
async def proof_recent(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    snapshot = compose_recent_proof_receipts(tenant, limit=8)
    return snapshot.model_dump(mode="json")


@router.post("/mint", summary="Mint Proof-of-Hive receipt for artifact")
async def proof_mint(
    body: ProofMintRequest,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    _require_owner_or_admin(principal)
    if not settings.proof_of_hive_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Proof-of-Hive disabled.")
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User context missing.")
    try:
        receipt = await mint_proof_for_artifact(
            db,
            dashboard_user_id=user.id,
            artifact_type=body.artifact_type,
            artifact_id=body.artifact_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return receipt.model_dump(mode="json")


__all__ = ["public_router", "router"]
