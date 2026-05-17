"""Browser harness manager with guardrails for agent-driven web actions."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserContext, Error as PlaywrightError, Page, async_playwright
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.browser_session import (
    BrowserAutomationAction,
    BrowserAutomationSession,
)

_CRITICAL_SELECTOR_TOKENS: tuple[str, ...] = ("submit", "delete", "purchase", "pay", "confirm")
_CRITICAL_ACTIONS: tuple[str, ...] = ("click", "submit")
_ALLOWED_SCHEMES: tuple[str, ...] = ("http", "https")


@dataclass(slots=True)
class _RuntimeSession:
    context: BrowserContext
    page: Page
    created_at: datetime


class BrowserGuardrailError(ValueError):
    """Raised when browser action violates configured policy."""


class BrowserManager:
    """Safe browser automation manager for supervisor and sub-agent workflows."""

    _playwright = None
    _browsers: dict[str, Browser] = {}
    _lock: asyncio.Lock = asyncio.Lock()
    _runtime_sessions: dict[uuid.UUID, _RuntimeSession] = {}

    @classmethod
    def _default_allowed_domains(cls) -> list[str]:
        raw = [item.strip().lower() for item in list(getattr(settings, "browser_allowed_domains", []) or [])]
        sanitized = [item for item in raw if item]
        if sanitized:
            return sanitized
        return ["example.com", "www.example.com", "queenswarm.love"]

    @classmethod
    def _is_domain_allowed(cls, hostname: str, allowed_domains: list[str]) -> bool:
        host = hostname.strip().lower()
        if not host:
            return False
        for domain in allowed_domains:
            dom = domain.strip().lower()
            if not dom:
                continue
            if host == dom or host.endswith(f".{dom}"):
                return True
        return False

    @classmethod
    def _assert_url_allowed(cls, url: str, allowed_domains: list[str]) -> None:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            msg = "Only http/https URLs are allowed."
            raise BrowserGuardrailError(msg)
        host = (parsed.hostname or "").strip().lower()
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                msg = f"Private/local network hosts are blocked: {host}"
                raise BrowserGuardrailError(msg)
        except ValueError:
            pass
        if not cls._is_domain_allowed(parsed.hostname or "", allowed_domains):
            msg = f"Domain is not allowed: {parsed.hostname or 'unknown'}"
            raise BrowserGuardrailError(msg)

    @classmethod
    def _is_critical_action(cls, *, action_type: str, selector: str | None) -> bool:
        if action_type in _CRITICAL_ACTIONS:
            return True
        if not selector:
            return False
        lowered = selector.lower()
        return any(token in lowered for token in _CRITICAL_SELECTOR_TOKENS)

    @classmethod
    async def _ensure_browser(cls, *, headless: bool) -> Browser:
        async with cls._lock:
            mode_key = "headless" if headless else "visible"
            existing = cls._browsers.get(mode_key)
            if existing is not None:
                return existing
            if cls._playwright is None:
                cls._playwright = await async_playwright().start()
            browser = await cls._playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-sync",
                ],
            )
            cls._browsers[mode_key] = browser
            return browser

    @classmethod
    async def _ensure_runtime_session(
        cls,
        db: AsyncSession,
        *,
        session_row: BrowserAutomationSession,
    ) -> _RuntimeSession:
        existing = cls._runtime_sessions.get(session_row.id)
        if existing is not None:
            return existing

        browser = await cls._ensure_browser(headless=bool(session_row.is_headless))
        context = await browser.new_context(
            accept_downloads=False,
            java_script_enabled=True,
            bypass_csp=False,
            user_agent="QueenswarmBrowserHarness/1.0",
        )
        page = await context.new_page()
        runtime = _RuntimeSession(context=context, page=page, created_at=datetime.now(tz=UTC))
        cls._runtime_sessions[session_row.id] = runtime
        session_row.started_at = datetime.now(tz=UTC)
        await db.flush()
        return runtime

    @classmethod
    async def create_session(
        cls,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        supervisor_session_id: uuid.UUID | None,
        sub_agent_session_id: uuid.UUID | None,
        created_by_subject: str | None,
        start_url: str | None,
        mode: str,
        allowed_domains: list[str] | None,
    ) -> BrowserAutomationSession:
        if len(cls._runtime_sessions) >= int(settings.browser_max_concurrent_sessions):
            msg = "Browser harness concurrent session limit reached."
            raise BrowserGuardrailError(msg)
        domains = [item.strip().lower() for item in (allowed_domains or cls._default_allowed_domains()) if item.strip()]
        row = BrowserAutomationSession(
            tenant_id=tenant_id,
            supervisor_session_id=supervisor_session_id,
            sub_agent_session_id=sub_agent_session_id,
            created_by_subject=created_by_subject,
            mode="visible" if mode == "visible" else "headless",
            status="running",
            start_url=start_url,
            current_url=start_url,
            allowed_domains=domains,
            expires_at=datetime.now(tz=UTC) + timedelta(seconds=int(settings.browser_session_ttl_sec)),
            max_actions=int(settings.browser_max_actions_per_session),
            actions_used=0,
            pending_approval_action={},
            is_headless=False if mode == "visible" else True,
        )
        db.add(row)
        await db.flush()
        await cls._record_action(
            db,
            session_row=row,
            action_type="session_start",
            status="ok",
            requires_approval=False,
            payload={
                "mode": row.mode,
                "allowed_domains": domains,
                "cpu_limit": float(settings.browser_instance_cpu_limit),
                "memory_mb": int(settings.browser_instance_memory_mb),
            },
            result_summary="Browser session started.",
        )
        if start_url:
            await cls.execute_action(
                db,
                session_row=row,
                action_type="navigate",
                payload={"url": start_url},
                approved=True,
            )
        return row

    @classmethod
    async def list_sessions(
        cls,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        limit: int = 40,
    ) -> list[BrowserAutomationSession]:
        stmt = select(BrowserAutomationSession)
        if tenant_id is not None:
            stmt = stmt.where(BrowserAutomationSession.tenant_id == tenant_id)
        stmt = stmt.order_by(desc(BrowserAutomationSession.created_at)).limit(max(1, min(limit, 120)))
        return list((await db.scalars(stmt)).all())

    @classmethod
    async def _record_action(
        cls,
        db: AsyncSession,
        *,
        session_row: BrowserAutomationSession,
        action_type: str,
        status: str,
        requires_approval: bool,
        payload: dict[str, Any],
        result_summary: str,
    ) -> BrowserAutomationAction:
        action = BrowserAutomationAction(
            tenant_id=session_row.tenant_id,
            browser_session_id=session_row.id,
            action_type=action_type[:32],
            status=status[:24],
            requires_approval=requires_approval,
            payload=dict(payload),
            result_summary=result_summary[:2000],
            occurred_at=datetime.now(tz=UTC),
        )
        db.add(action)
        await db.flush()
        return action

    @classmethod
    async def execute_action(
        cls,
        db: AsyncSession,
        *,
        session_row: BrowserAutomationSession,
        action_type: str,
        payload: dict[str, Any],
        approved: bool = False,
    ) -> dict[str, Any]:
        if session_row.status != "running":
            msg = "Browser session is not running."
            raise BrowserGuardrailError(msg)
        now = datetime.now(tz=UTC)
        if session_row.expires_at is not None and now >= session_row.expires_at:
            session_row.status = "expired"
            session_row.ended_at = now
            await cls._record_action(
                db,
                session_row=session_row,
                action_type=action_type,
                status="blocked",
                requires_approval=False,
                payload=payload,
                result_summary="Session expired by TTL guardrail.",
            )
            msg = "Browser session expired."
            raise BrowserGuardrailError(msg)
        if int(session_row.actions_used or 0) >= int(session_row.max_actions or settings.browser_max_actions_per_session):
            session_row.status = "limit_reached"
            session_row.ended_at = now
            await cls._record_action(
                db,
                session_row=session_row,
                action_type=action_type,
                status="blocked",
                requires_approval=False,
                payload=payload,
                result_summary="Session action limit reached.",
            )
            msg = "Action limit reached for browser session."
            raise BrowserGuardrailError(msg)

        normalized = action_type.strip().lower()
        selector = str(payload.get("selector") or "").strip() or None
        if cls._is_critical_action(action_type=normalized, selector=selector) and not approved:
            session_row.pending_approval_action = {
                "action_type": normalized,
                "payload": dict(payload),
                "requested_at": now.isoformat(),
            }
            await cls._record_action(
                db,
                session_row=session_row,
                action_type=normalized,
                status="pending_approval",
                requires_approval=True,
                payload=payload,
                result_summary="Awaiting manual approval for critical browser action.",
            )
            await db.flush()
            return {"status": "pending_approval", "requires_approval": True}

        target_url = str(payload.get("url") or "").strip()
        if normalized == "navigate":
            cls._assert_url_allowed(target_url, list(session_row.allowed_domains or []))
        if normalized in {"click", "fill"} and not selector:
            msg = f"Selector is required for {normalized}."
            raise BrowserGuardrailError(msg)

        runtime = await cls._ensure_runtime_session(db, session_row=session_row)
        page = runtime.page
        timeout_ms = max(1000, int(settings.browser_action_timeout_sec) * 1000)

        try:
            if normalized == "navigate":
                await page.goto(target_url, timeout=timeout_ms, wait_until="domcontentloaded")
                session_row.current_url = target_url
                result_summary = f"Navigated to {target_url}"
            elif normalized == "click":
                await page.click(selector, timeout=timeout_ms)
                result_summary = f"Clicked selector: {selector}"
            elif normalized == "fill":
                text_value = str(payload.get("text") or "")
                await page.fill(selector, text_value, timeout=timeout_ms)
                result_summary = f"Filled selector: {selector}"
            elif normalized == "scrape":
                query = selector or "body"
                content = await page.text_content(query, timeout=timeout_ms)
                session_row.last_snapshot_text = (content or "").strip()[:12000]
                result_summary = f"Scraped text from {query}"
            elif normalized == "snapshot":
                result_summary = "Captured page snapshot."
            else:
                msg = f"Unsupported browser action: {normalized}"
                raise BrowserGuardrailError(msg)

            screenshot_bytes = await page.screenshot(type="jpeg", quality=60, full_page=False)
            session_row.last_screenshot_base64 = base64.b64encode(screenshot_bytes).decode("ascii")
            session_row.current_url = page.url
            session_row.actions_used = int(session_row.actions_used or 0) + 1
            session_row.pending_approval_action = {}
            await cls._record_action(
                db,
                session_row=session_row,
                action_type=normalized,
                status="ok",
                requires_approval=False,
                payload=payload,
                result_summary=result_summary,
            )
            await db.flush()
            return {
                "status": "ok",
                "result_summary": result_summary,
                "current_url": session_row.current_url,
                "snapshot_text": (session_row.last_snapshot_text or "")[:1200],
            }
        except (PlaywrightError, BrowserGuardrailError) as exc:
            message = str(exc)[:500]
            session_row.blocked_reason = message
            await cls._record_action(
                db,
                session_row=session_row,
                action_type=normalized,
                status="blocked",
                requires_approval=False,
                payload=payload,
                result_summary=message,
            )
            await db.flush()
            raise

    @classmethod
    async def approve_pending_action(
        cls,
        db: AsyncSession,
        *,
        session_row: BrowserAutomationSession,
        approve: bool,
    ) -> dict[str, Any]:
        pending = dict(session_row.pending_approval_action or {})
        if not pending:
            return {"status": "no_pending_action"}
        action_type = str(pending.get("action_type") or "").strip().lower()
        payload = dict(pending.get("payload") or {})
        if not approve:
            session_row.pending_approval_action = {}
            await cls._record_action(
                db,
                session_row=session_row,
                action_type=action_type or "pending",
                status="rejected",
                requires_approval=True,
                payload=payload,
                result_summary="Critical action rejected by operator.",
            )
            await db.flush()
            return {"status": "rejected"}
        return await cls.execute_action(
            db,
            session_row=session_row,
            action_type=action_type,
            payload=payload,
            approved=True,
        )

    @classmethod
    async def close_session(cls, db: AsyncSession, *, session_row: BrowserAutomationSession) -> None:
        runtime = cls._runtime_sessions.pop(session_row.id, None)
        if runtime is not None:
            await runtime.context.close()
        session_row.status = "closed"
        session_row.ended_at = datetime.now(tz=UTC)
        await cls._record_action(
            db,
            session_row=session_row,
            action_type="session_close",
            status="ok",
            requires_approval=False,
            payload={},
            result_summary="Browser session closed.",
        )
        await db.flush()

    @classmethod
    async def run_goal_step(
        cls,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        supervisor_session_id: uuid.UUID,
        sub_agent_session_id: uuid.UUID,
        created_by_subject: str | None,
        goal: str,
        existing_session_id: uuid.UUID | None,
        mode: str = "headless",
    ) -> dict[str, Any]:
        """Execute one browser-assisted step for a goal (navigate + scrape baseline)."""

        session_row: BrowserAutomationSession | None = None
        if existing_session_id is not None:
            session_row = await db.get(BrowserAutomationSession, existing_session_id)
        if session_row is None:
            matched = re.search(r"https?://[^\s]+", goal)
            start_url = matched.group(0) if matched else "https://example.com"
            session_row = await cls.create_session(
                db,
                tenant_id=tenant_id,
                supervisor_session_id=supervisor_session_id,
                sub_agent_session_id=sub_agent_session_id,
                created_by_subject=created_by_subject,
                start_url=start_url,
                mode=mode,
                allowed_domains=None,
            )
        if session_row.current_url:
            await cls.execute_action(
                db,
                session_row=session_row,
                action_type="navigate",
                payload={"url": session_row.current_url},
                approved=True,
            )
        scrape_result = await cls.execute_action(
            db,
            session_row=session_row,
            action_type="scrape",
            payload={"selector": "body"},
            approved=True,
        )
        return {
            "browser_session_id": str(session_row.id),
            "current_url": session_row.current_url,
            "snapshot_text": scrape_result.get("snapshot_text") or "",
            "actions_used": int(session_row.actions_used or 0),
        }


__all__ = ["BrowserGuardrailError", "BrowserManager"]
