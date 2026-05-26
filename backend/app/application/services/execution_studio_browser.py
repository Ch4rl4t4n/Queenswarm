"""Governed browser harness fallback lane for Execution Studio."""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio import studio_policy
from app.application.services.execution_studio_activity import persist_execution_activity
from app.core.config import get_settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.tools.browser_manager import BrowserGuardrailError, BrowserManager

ExecutionMode = Literal["draft", "simulate", "live"]

_URL_PATTERN = re.compile(r"https?://[^\s]+")


def _resolve_start_url(*, goal: str, start_url: str | None) -> str:
    """Pick start URL from explicit param or first URL token in goal."""

    if start_url and start_url.strip():
        return start_url.strip()
    matched = _URL_PATTERN.search(goal)
    if matched:
        return matched.group(0)
    return "https://example.com"


async def execute_browser_fallback_step(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    dashboard_user_id: uuid.UUID,
    goal: str,
    start_url: str | None = None,
    mode: ExecutionMode | None = None,
    operator_confirmed: bool = False,
) -> dict[str, Any]:
    """Governed browser harness step — draft / simulate / live."""

    settings = get_settings()
    if not settings.execution_studio_enabled:
        return {"ok": False, "error": "execution_studio_disabled"}

    policy = studio_policy(tenant)
    resolved_mode: ExecutionMode = mode or policy["default_mode"]  # type: ignore[assignment]
    url = _resolve_start_url(goal=goal, start_url=start_url)
    preview = {
        "goal_excerpt": goal.strip()[:500],
        "start_url": url,
        "lane": "browser_fallback",
        "harness_enabled": bool(settings.browser_harness_enabled),
    }

    if resolved_mode == "draft":
        result = {
            "ok": True,
            "mode": "draft",
            "executed": False,
            "preview": preview,
            "message": "Browser fallback preview — no harness session started.",
        }
        await persist_execution_activity(
            session,
            tenant,
            event_type="browser_step",
            message=f"Browser draft: {url[:80]}",
            payload={"mode": "draft", "url": url},
        )
        return result

    if resolved_mode == "simulate":
        result = {
            "ok": True,
            "mode": "simulate",
            "executed": False,
            "preview": preview,
            "simulated_result": {
                "current_url": url,
                "snapshot_excerpt": f"[simulated] Would navigate to {url} and scrape body for: {goal[:120]}",
            },
            "message": "Simulated browser harness step.",
        }
        await persist_execution_activity(
            session,
            tenant,
            event_type="browser_step",
            message=f"Browser simulate: {url[:80]}",
            payload={"mode": "simulate", "url": url},
        )
        return result

    if not settings.browser_harness_enabled:
        return {"ok": False, "error": "browser_harness_disabled", "mode": "live", "preview": preview}

    if policy.get("live_requires_approval") and not operator_confirmed:
        return {
            "ok": False,
            "error": "approval_required",
            "mode": "live",
            "preview": preview,
            "message": "Confirm live browser harness step in Execution Studio.",
        }

    if operator_confirmed:
        from app.application.services.execution_studio_confirm_guard import (
            ExecutionStudioConfirmThrottledError,
            assert_operator_confirm_allowed,
        )

        try:
            await assert_operator_confirm_allowed(
                tenant_id=tenant.id if tenant is not None else None,
                lane="browser",
            )
        except ExecutionStudioConfirmThrottledError as exc:
            return {
                "ok": False,
                "error": "confirm_throttled",
                "mode": "live",
                "preview": preview,
                "retry_after_sec": exc.retry_after_sec,
                "message": "Please wait before confirming another live browser step.",
            }

    subject = f"dashboard:{dashboard_user_id}"
    try:
        browser_row = await BrowserManager.create_session(
            session,
            tenant_id=tenant.id if tenant is not None else None,
            supervisor_session_id=None,
            sub_agent_session_id=None,
            created_by_subject=subject,
            start_url=url,
            mode="headless",
            allowed_domains=None,
        )
        await BrowserManager.execute_action(
            session,
            session_row=browser_row,
            action_type="navigate",
            payload={"url": url},
            approved=True,
        )
        scrape = await BrowserManager.execute_action(
            session,
            session_row=browser_row,
            action_type="scrape",
            payload={"selector": "body"},
            approved=True,
        )
        snapshot = str(scrape.get("snapshot_text") or "")[:2000]
        result = {
            "ok": True,
            "mode": "live",
            "executed": True,
            "preview": preview,
            "result": {
                "browser_session_id": str(browser_row.id),
                "current_url": browser_row.current_url,
                "snapshot_text": snapshot,
                "actions_used": int(browser_row.actions_used or 0),
            },
        }
        await persist_execution_activity(
            session,
            tenant,
            event_type="browser_step",
            message=f"Browser live: {browser_row.current_url or url}",
            payload={"mode": "live", "browser_session_id": str(browser_row.id)},
        )
        if operator_confirmed:
            from app.application.services.execution_studio_activity import persist_pending_live_cleared

            await persist_pending_live_cleared(session, tenant, lane="browser")
        return result
    except BrowserGuardrailError as exc:
        return {
            "ok": False,
            "error": "browser_guardrail",
            "mode": "live",
            "preview": preview,
            "message": str(exc)[:400],
        }


__all__ = ["execute_browser_fallback_step"]
