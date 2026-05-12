"""Hive plugin manifest for Phase G dashboard (JWT guarded)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import JwtSubject
from app.core.logging import get_logger
from app.services.plugin_hub import bump_plugin_generation, plugin_manifest

router = APIRouter(tags=["Plugins"])
logger = get_logger(__name__)


class PluginToggleBody(BaseModel):
    """Stub body for dashboard toggles."""

    enabled: bool | None = None


@router.get("", summary="List installed hive plugins")
async def plugins_list(_subject: JwtSubject) -> dict[str, Any]:
    """Return deterministic plugin rows for cockpit wiring."""

    m = plugin_manifest()
    enriched: list[dict[str, Any]] = []
    for row in m.get("plugins", []):
        rid = row.get("id")
        enriched.append(
            {
                **row,
                "version": "2026.05.12",
                "status": "active" if row.get("enabled") else "inactive",
            },
        )
    return {"reload_generation": m.get("reload_generation"), "installed": enriched}


@router.patch("/{plugin_id}", summary="Enable or disable plugin (best-effort stub)")
async def plugins_patch(plugin_id: str, body: PluginToggleBody, _subject: JwtSubject) -> dict[str, Any]:
    """Toggle fields are echoed only until dynamic plugin manifests land."""

    _ = plugin_id
    _ = body
    bump_plugin_generation()
    logger.info("plugins.catalog.patch_stub", plugin_id=plugin_id, actor=_subject)
    return {"ok": True, "plugin_id": plugin_id, "applied": {"enabled": body.enabled}}


@router.delete("/{plugin_id}", summary="Remove plugin (not supported)")
async def plugins_delete(plugin_id: str, _subject: JwtSubject) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Runtime plugin unload is disabled for this hive build.",
    )


@router.post("/upload", summary="Upload Python plugin artifact (disabled)")
async def plugins_upload(_subject: JwtSubject, file: UploadFile | None = File(default=None)) -> None:
    _ = file
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Plugin ZIP/.py ingestion is gated — configure integrations via Compose env.",
    )


__all__ = ["router"]
