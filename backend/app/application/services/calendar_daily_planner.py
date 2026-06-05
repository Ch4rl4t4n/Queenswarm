"""PA2 — Google Calendar → proactive daily planner items (read-only)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService, invoke_dynamic_tool

_logger = get_logger(__name__)


class CalendarEventPlanItemOut(BaseModel):
    """One calendar block surfaced in the daily plan."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    detail: str = ""
    href: str = "/integrations?tab=studio"


class CalendarDailyPlannerOut(BaseModel):
    """Calendar slice for solo daily plan / CBO."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    connected: bool = False
    generated_at: datetime
    event_count: int = 0
    items: list[CalendarEventPlanItemOut] = Field(default_factory=list)
    message: str = ""


def _parse_event_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_events_payload(body: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return []
    items = payload.get("items")
    return [row for row in items if isinstance(row, dict)] if isinstance(items, list) else []


async def compose_calendar_daily_planner(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    horizon_hours: int = 18,
) -> CalendarDailyPlannerOut:
    """List today's calendar events via google_calendar connector (no LLM)."""

    now = datetime.now(tz=UTC)
    if not settings.calendar_daily_planner_enabled:
        return CalendarDailyPlannerOut(
            enabled=False,
            generated_at=now,
            message="Calendar daily planner disabled.",
        )

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug="google_calendar")
    if row is None or not row.is_active:
        return CalendarDailyPlannerOut(
            enabled=True,
            connected=False,
            generated_at=now,
            message="Connect Google Calendar in Integrations → Connectors.",
        )

    time_min = now.isoformat().replace("+00:00", "Z")
    time_max = (now + timedelta(hours=max(4, min(horizon_hours, 48)))).isoformat().replace("+00:00", "Z")
    raw = await invoke_dynamic_tool(
        session,
        connector_slug="google_calendar",
        tool_name="events_list",
        arguments={
            "calendar_id": "primary",
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "12",
        },
        agent_task_id=f"calendar_planner_{dashboard_user_id}",
    )
    if raw.startswith("dynamic_invoke"):
        _logger.warning(
            "calendar_daily_planner.fetch_failed",
            agent_id="calendar_planner",
            task_id=str(dashboard_user_id),
            error=raw[:200],
        )
        return CalendarDailyPlannerOut(
            enabled=True,
            connected=True,
            generated_at=now,
            message="Calendar fetch failed — re-authorize OAuth.",
        )

    items: list[CalendarEventPlanItemOut] = []
    for event in _parse_events_payload(raw):
        start_raw = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get("date")
        end_raw = (event.get("end") or {}).get("dateTime") or (event.get("end") or {}).get("date")
        title = str(event.get("summary") or "Calendar event").strip()[:120]
        eid = str(event.get("id") or title)[:64]
        items.append(
            CalendarEventPlanItemOut(
                id=f"cal_{eid}",
                title=title,
                start_at=_parse_event_time(str(start_raw) if start_raw else None),
                end_at=_parse_event_time(str(end_raw) if end_raw else None),
                detail="From Google Calendar — plan supervisor work around this block.",
            ),
        )

    return CalendarDailyPlannerOut(
        enabled=True,
        connected=True,
        generated_at=now,
        event_count=len(items),
        items=items[:8],
        message=f"{len(items)} upcoming event(s)." if items else "No events in window — deep work block open.",
    )


__all__ = ["CalendarDailyPlannerOut", "CalendarEventPlanItemOut", "compose_calendar_daily_planner"]
