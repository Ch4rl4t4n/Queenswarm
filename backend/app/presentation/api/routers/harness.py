"""AI Layer harness visibility API."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.forager_intelligence import run_intelligence_scan
from app.application.services.forager_intelligence_v2 import ForagerV2SnapshotOut, compose_forager_v2_snapshot
from app.application.services.harness_four_cs_audit import compose_four_cs_audit
from app.application.services.harness_snapshot import build_harness_snapshot
from app.application.services.pattern_explorer import build_pattern_explorer_payload
from app.application.services.self_extending_marketplace import (
    SelfExtendingMarketplaceDisabledError,
    SelfExtendingUnsupportedProposalError,
    apply_intelligence_proposal,
    build_enriched_intelligence_scan,
)
from app.application.services.lsp.lsp_mcp_bridge import (
    LspBridgeDisabledError,
    LspBridgeToolError,
    bridge_status,
    invoke_lsp_tool,
)
from app.application.services.rubric_templates import (
    evaluate_text_with_rubric,
    get_rubric_template,
    list_rubric_templates,
    merge_rubric_into_criteria,
)
from app.application.services.slack_harness_trainer import (
    SlackHarnessTrainerConfigError,
    SlackHarnessTrainerDisabledError,
    SlackHarnessTrainerForbiddenError,
    SlackHarnessTrainerValidationError,
    append_behavioral_feedback,
    notify_trainer_confirmation,
    resolve_slack_trainer_tenant_id,
    verify_slack_request_signature,
)
from app.common.schemas.lsp_bridge import (
    LspFileSymbolsRequest,
    LspFindReferencesRequest,
    LspResolveRequest,
    LspToolInvokeRequest,
)
from app.common.schemas.slack_harness_trainer import (
    SlackTrainerFeedbackRequest,
    SlackTrainerFeedbackResponse,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role, require_tenant_permission

router = APIRouter(prefix="/harness", tags=["Harness"])


@router.get("/snapshot", summary="AI Layer harness snapshot")
async def harness_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return layered rules, skills, MCP tools, monitoring, and recent agentic pattern usage."""

    tenant_id = principal.get("tenant_id")
    return await build_harness_snapshot(db, tenant_id=tenant_id)


@router.get("/four-cs-audit", summary="Four Cs readiness audit (context, connections, capabilities, cadence)")
async def harness_four_cs_audit(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Read-only Nate Herk-style AI OS readiness score for operator harness."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    audit = await compose_four_cs_audit(db, tenant_id=tenant_id)
    return audit.model_dump(mode="json")


@router.get("/pattern-explorer", summary="Agentic pattern usage explorer")
async def harness_pattern_explorer(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return pattern catalog, today's usage tallies, and recent session rationale."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await build_pattern_explorer_payload(db, tenant_id=tenant_id)


@router.post("/intelligence-scan", summary="Forager Intelligence Loop scan (read-only proposals)")
async def harness_intelligence_scan(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Propose skill/MCP/doc refresh candidates; enrich MCP presets with install actions."""

    if settings.self_extending_tool_marketplace_enabled:
        user = principal.get("user")
        user_id = getattr(user, "id", None)
        tenant_id = principal.get("tenant_id")
        if user_id is not None:
            return await build_enriched_intelligence_scan(
                db,
                dashboard_user_id=user_id,
                tenant_id=tenant_id if isinstance(tenant_id, uuid.UUID) else None,
            )
    return run_intelligence_scan()


@router.get("/forager-v2", response_model=ForagerV2SnapshotOut, summary="Forager Intelligence v2 snapshot")
async def harness_forager_v2_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerV2SnapshotOut:
    """Tenant-scoped forager scan with connector gaps and MCP proposals."""

    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    tenant = await db.get(Tenant, tenant_id) if tenant_id is not None else None
    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    return await compose_forager_v2_snapshot(
        db,
        tenant=tenant,
        dashboard_user_id=user_id,
    )


class IntelligenceApplyBody(BaseModel):
    """Apply one Forager intelligence proposal (MCP preset install)."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=2, max_length=64)
    target: str = Field(min_length=2, max_length=160)


@router.post("/intelligence-apply", summary="Apply Forager MCP preset proposal (one-click install)")
async def harness_intelligence_apply(
    body: IntelligenceApplyBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Self-extending marketplace — install Phase3 template from intelligence scan."""

    user = principal.get("user")
    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    try:
        result = await apply_intelligence_proposal(
            db,
            dashboard_user_id=user_id,
            kind=body.kind,
            target=body.target,
        )
        await db.commit()
    except SelfExtendingMarketplaceDisabledError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SelfExtendingUnsupportedProposalError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except KeyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return result


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@router.post(
    "/slack-trainer/feedback",
    response_model=SlackTrainerFeedbackResponse,
    summary="Append dashboard feedback to behavioral INSTRUCTIONS memory",
)
async def harness_slack_trainer_feedback(
    body: SlackTrainerFeedbackRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SlackTrainerFeedbackResponse:
    """AnswerThis-style trainer — non-technical operators teach Queen via text feedback."""

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    author = getattr(user, "email", None) or getattr(user, "display_name", None)
    user_id = getattr(user, "id", None)
    role = str(principal.get("tenant_role") or "guest")
    is_admin = role in {"owner", "admin"}
    try:
        result = await append_behavioral_feedback(
            db,
            tenant_id=tenant_id,
            feedback=body.feedback,
            source=body.source,
            author=str(author) if author else None,
            user_id=user_id,
            is_admin=is_admin,
        )
        await db.commit()
    except SlackHarnessTrainerDisabledError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SlackHarnessTrainerForbiddenError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SlackHarnessTrainerValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    slack_notified = await notify_trainer_confirmation(
        feedback_preview=body.feedback,
        author=str(author) if author else None,
    )
    return SlackTrainerFeedbackResponse(
        tenant_id=result.tenant_id,
        kind=result.kind.value,
        version=result.version,
        char_count=result.char_count,
        appended_chars=result.appended_chars,
        source=result.source,
        author=result.author,
        slack_notified=slack_notified,
    )


class SlackSlashCommandResponse(BaseModel):
    """Slack-compatible slash command JSON body."""

    model_config = ConfigDict(extra="ignore")

    response_type: str = Field(default="ephemeral")
    text: str


@router.post(
    "/slack-trainer/slack-command",
    response_model=SlackSlashCommandResponse,
    include_in_schema=False,
    summary="Slack slash command ingress (unsigned — verifies X-Slack-Signature)",
)
async def harness_slack_trainer_slash_command(
    request: Request,
    db: DbSession,
) -> SlackSlashCommandResponse:
    """Receive ``/queen-train`` style slash commands and append to INSTRUCTIONS memory."""

    signing_secret = (settings.slack_harness_trainer_signing_secret or "").strip()
    if not signing_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack signing secret is not configured.",
        )

    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not verify_slack_request_signature(
        signing_secret=signing_secret,
        timestamp=timestamp,
        body=body,
        signature=signature,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature.")

    form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    feedback = (form.get("text") or [""])[0].strip()
    user_name = (form.get("user_name") or ["slack-user"])[0].strip()

    try:
        tenant_id = await resolve_slack_trainer_tenant_id(db)
        result = await append_behavioral_feedback(
            db,
            tenant_id=tenant_id,
            feedback=feedback,
            source="slack_slash",
            author=user_name,
            user_id=None,
            is_admin=True,
        )
        await db.commit()
    except SlackHarnessTrainerDisabledError as exc:
        await db.rollback()
        return SlackSlashCommandResponse(text=f"Trainer disabled: {exc}")
    except SlackHarnessTrainerConfigError as exc:
        await db.rollback()
        return SlackSlashCommandResponse(text=f"Trainer misconfigured: {exc}")
    except SlackHarnessTrainerForbiddenError as exc:
        await db.rollback()
        return SlackSlashCommandResponse(text=str(exc))
    except SlackHarnessTrainerValidationError as exc:
        await db.rollback()
        return SlackSlashCommandResponse(text=str(exc))

    preview = feedback.replace("\n", " ")[:180]
    return SlackSlashCommandResponse(
        text=(
            f"Saved to behavioral memory (v{result.version}, {result.char_count} chars).\n"
            f"> {preview}"
        ),
    )


@router.get("/lsp-bridge/status", summary="LSP + MCP bridge deployment status")
async def harness_lsp_bridge_status(
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return symbol bridge config (no secrets)."""

    return bridge_status()


@router.post("/lsp-bridge/resolve", summary="Resolve a symbol name in the monorepo")
async def harness_lsp_bridge_resolve(
    body: LspResolveRequest,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Harness tester for ``resolve_symbol`` MCP tool."""

    try:
        return invoke_lsp_tool("resolve_symbol", {"query": body.query})
    except LspBridgeDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LspBridgeToolError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/lsp-bridge/file-symbols", summary="List symbols in one repo file")
async def harness_lsp_bridge_file_symbols(
    body: LspFileSymbolsRequest,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Harness tester for ``list_file_symbols`` MCP tool."""

    try:
        return invoke_lsp_tool("list_file_symbols", {"path": body.path})
    except LspBridgeDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LspBridgeToolError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/lsp-bridge/find-references", summary="Find references to a symbol")
async def harness_lsp_bridge_find_references(
    body: LspFindReferencesRequest,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Harness tester for ``find_references`` MCP tool."""

    try:
        return invoke_lsp_tool("find_references", {"symbol": body.symbol})
    except LspBridgeDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LspBridgeToolError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/lsp-bridge/invoke", summary="Generic LSP MCP tool invoke (harness)")
async def harness_lsp_bridge_invoke(
    body: LspToolInvokeRequest,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Dispatch any builtin LSP bridge tool by name."""

    try:
        return invoke_lsp_tool(body.tool_name, body.arguments)
    except LspBridgeDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LspBridgeToolError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


class RubricApplyRequest(BaseModel):
    """Merge a rubric template into workflow evaluation criteria."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(min_length=2, max_length=64)
    base_criteria: dict[str, Any] = Field(default_factory=dict)


class RubricEvaluateRequest(BaseModel):
    """Score sample text against a curated rubric template."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(min_length=2, max_length=64)
    text: str = Field(min_length=8, max_length=12000)


def _require_rubric_templates_enabled() -> None:
    if not settings.rubric_templates_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rubric templates are disabled (RUBRIC_TEMPLATES_ENABLED=false).",
        )


@router.get("/rubric-templates", summary="List curated subjective scoring rubrics")
async def harness_rubric_templates_list(
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> list[dict[str, Any]]:
    """Return design, copy, PRD, code review, and a11y rubric templates."""

    _require_rubric_templates_enabled()
    return [item.model_dump() for item in list_rubric_templates()]


@router.post("/rubric-templates/apply", summary="Merge rubric into evaluation_criteria")
async def harness_rubric_templates_apply(
    body: RubricApplyRequest,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Harness helper — copy merged criteria into workflow step definitions."""

    _require_rubric_templates_enabled()
    try:
        merged = merge_rubric_into_criteria(body.base_criteria, body.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return {"evaluation_criteria": merged}


@router.post("/rubric-templates/evaluate", summary="Evaluate sample text with rubric")
async def harness_rubric_templates_evaluate(
    body: RubricEvaluateRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Run generator-evaluator scoring against a rubric template."""

    _require_rubric_templates_enabled()
    if get_rubric_template(body.template_id) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown rubric template.")
    try:
        return await evaluate_text_with_rubric(
            db,
            text=body.text,
            template_id=body.template_id,
            swarm_id=str(principal.get("tenant_id") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


__all__ = ["router"]
