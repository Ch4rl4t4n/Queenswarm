"""AI Layer harness visibility API."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.forager_intelligence import run_intelligence_scan
from app.application.services.harness_snapshot import build_harness_snapshot
from app.application.services.pattern_explorer import build_pattern_explorer_payload
from app.application.services.lsp.lsp_mcp_bridge import (
    LspBridgeDisabledError,
    LspBridgeToolError,
    bridge_status,
    invoke_lsp_tool,
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
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/harness", tags=["Harness"])


@router.get("/snapshot", summary="AI Layer harness snapshot")
async def harness_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return layered rules, skills, MCP tools, monitoring, and recent agentic pattern usage."""

    tenant_id = principal.get("tenant_id")
    return await build_harness_snapshot(db, tenant_id=tenant_id)


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
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Propose skill/MCP/doc refresh candidates without mutating the hive."""

    return run_intelligence_scan()


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


__all__ = ["router"]
