"""Hive plugin catalog + user ``.py`` uploads (JWT guarded)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.presentation.api.deps import JwtSubject
from app.core.logging import get_logger
from app.infrastructure.plugins.manager import (
    PLUGIN_DIR,
    discover_plugins,
    load_plugin,
    unload_plugin,
)
from app.application.services.plugin_hub import bump_plugin_generation, plugin_manifest

router = APIRouter(tags=["Plugins"])
logger = get_logger(__name__)


class PluginToggleBody(BaseModel):
    """Stub body for dashboard toggles affecting built-in rows."""

    model_config = {"extra": "ignore"}

    enabled: bool | None = None


def _builtin_rows() -> list[dict[str, Any]]:
    """Normalize static hub manifest into API rows."""

    enriched: list[dict[str, Any]] = []
    for row in plugin_manifest().get("plugins", []):
        rid = str(row.get("id", ""))
        enriched.append(
            {
                "id": rid,
                "title": row.get("title", rid),
                "name": row.get("title", rid),
                "enabled": bool(row.get("enabled")),
                "description": row.get("description", ""),
                "version": "bundled",
                "status": "active" if row.get("enabled") else "inactive",
                "source": "builtin",
            },
        )
    return enriched


@router.get("", summary="List built-in + user plugins")
async def plugins_list(_subject: JwtSubject) -> dict[str, Any]:
    """Return manifest rows plus discovered user ``.py`` plugins."""

    m = plugin_manifest()
    user = discover_plugins()
    return {
        "reload_generation": m.get("reload_generation"),
        "reloaded_at": m.get("reloaded_at"),
        "builtin": _builtin_rows(),
        "user": user,
        "installed": _builtin_rows()
        + [
            {
                "id": u["id"],
                "title": u["name"],
                "name": u["name"],
                "enabled": u["status"] == "active",
                "description": u["description"],
                "version": u["version"],
                "status": u["status"],
                "source": "user",
                "filename": u.get("filename"),
                "size_bytes": u.get("size_bytes"),
            }
            for u in user
        ],
    }


@router.post("/upload", summary="Upload a user Python plugin")
async def plugins_upload(_subject: JwtSubject, file: UploadFile = File(...)) -> dict[str, Any]:
    """Persist ``.py`` under the user plugin directory and attempt to load it."""

    name = Path(file.filename or "").name
    if not name.endswith(".py"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .py files allowed.")
    if name.startswith("_") or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    dest = PLUGIN_DIR / name
    try:
        with dest.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
    finally:
        await file.close()

    stem = name[:-3]
    try:
        meta = load_plugin(stem)
        bump_plugin_generation()
        logger.info("plugins.user.upload_ok", plugin=stem, actor=_subject)
        return {"status": "uploaded_and_loaded", "plugin": meta}
    except Exception as exc:  # noqa: BLE001
        logger.warning("plugins.user.upload_load_failed", plugin=stem, error=str(exc))
        bump_plugin_generation()
        return {
            "status": "uploaded",
            "warning": f"Auto-load failed: {exc}",
            "plugin_name": stem,
        }


@router.post("/{plugin_name}/enable", summary="Load or reload a user plugin")
async def enable_plugin(plugin_name: str, _subject: JwtSubject) -> dict[str, Any]:
    """Import module from disk (active)."""

    try:
        meta = load_plugin(plugin_name)
        bump_plugin_generation()
        logger.info("plugins.user.enabled", plugin=plugin_name, actor=_subject)
        return {"status": "enabled", "plugin": meta}
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin file not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plugin load failed: {exc}",
        ) from exc


@router.post("/{plugin_name}/disable", summary="Unload a user plugin")
async def disable_plugin(plugin_name: str, _subject: JwtSubject) -> dict[str, str]:
    """Remove module from import cache."""

    unload_plugin(plugin_name)
    bump_plugin_generation()
    logger.info("plugins.user.disabled", plugin=plugin_name, actor=_subject)
    return {"status": "disabled", "plugin_name": Path(plugin_name).name}


@router.patch("/{plugin_id}", summary="Toggle built-in plugin flags (stub)")
async def plugins_patch(plugin_id: str, body: PluginToggleBody, _subject: JwtSubject) -> dict[str, Any]:
    """Bump reload generation for UI cache busting."""

    _ = plugin_id
    _ = body
    gen = bump_plugin_generation()
    logger.info("plugins.catalog.patch_stub", plugin_id=plugin_id, actor=_subject, generation=gen)
    return {"ok": True, "plugin_id": plugin_id, "applied": {"enabled": body.enabled}, "reload_generation": gen}


@router.delete("/{plugin_name}", summary="Delete a user plugin file")
async def delete_user_plugin(plugin_name: str, _subject: JwtSubject) -> dict[str, str]:
    """Remove ``.py`` from disk (built-ins cannot be deleted)."""

    stem = Path(plugin_name).name
    path = PLUGIN_DIR / f"{stem}.py"
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User plugin not found.")
    unload_plugin(stem)
    path.unlink(missing_ok=True)
    bump_plugin_generation()
    logger.info("plugins.user.deleted", plugin=stem, actor=_subject)
    return {"status": "deleted", "plugin_name": stem}


__all__ = ["router"]
