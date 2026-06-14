"""Gumroad catalog URL auto-sync — API products → gumroad-upload-status.json."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.marketing_product_catalog import (
    _resolve_export_root,
    collect_catalog_products,
)
from app.application.services.skill_factory_gumroad_listing import _resolve_gumroad_token

logger = structlog.get_logger(__name__)

_GUMROAD_PRODUCTS_API = "https://api.gumroad.com/v2/products"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class GumroadCatalogSyncResult(BaseModel):
    """Outcome of a Gumroad → upload-status sync pass."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    synced_count: int = 0
    skipped_count: int = 0
    api_product_count: int = 0
    message: str = ""
    state_path: str = ""


def _slugify(value: str) -> str:
    """Normalize text to catalog slug form."""

    base = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return base[:120]


def _load_upload_state(state_path: Path) -> dict[str, Any]:
    """Load gumroad-upload-status.json."""

    if not state_path.is_file():
        return {"products": {}}
    try:
        import json

        loaded = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"products": {}}
    if not isinstance(loaded, dict):
        return {"products": {}}
    products = loaded.get("products")
    if not isinstance(products, dict):
        loaded["products"] = {}
    return loaded


def _save_upload_state(state_path: Path, state: dict[str, Any]) -> None:
    """Persist gumroad-upload-status.json."""

    import json

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _catalog_slug_index(export_root: Path) -> dict[str, str]:
    """Map normalized keys → canonical catalog slug."""

    index: dict[str, str] = {}
    for product in collect_catalog_products(export_root):
        slug = product.slug.strip()
        if not slug:
            continue
        index[_slugify(slug)] = slug
        family = _slugify(re.sub(r"-\d+$", "", slug.removesuffix("-simulate-first-pack")))
        index.setdefault(family, slug)
    return index


def match_gumroad_product_to_slug(product: dict[str, Any], slug_index: dict[str, str]) -> str | None:
    """Resolve one Gumroad API product row to a catalog slug."""

    permalink = str(product.get("custom_permalink") or product.get("permalink") or "").strip()
    if permalink:
        key = _slugify(permalink)
        if key in slug_index:
            return slug_index[key]

    short_url = str(product.get("short_url") or product.get("url") or "").strip()
    if short_url:
        tail = short_url.rstrip("/").split("/")[-1]
        key = _slugify(tail)
        if key in slug_index:
            return slug_index[key]

    name_key = _slugify(str(product.get("name") or ""))
    if name_key in slug_index:
        return slug_index[name_key]

    for key, slug in slug_index.items():
        if key and (key in name_key or name_key in key):
            return slug
    return None


async def fetch_gumroad_products(*, access_token: str) -> list[dict[str, Any]]:
    """List seller products from Gumroad REST API."""

    token = access_token.strip()
    if not token:
        return []
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(_GUMROAD_PRODUCTS_API, params={"access_token": token})
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or not payload.get("success"):
        return []
    products = payload.get("products")
    if not isinstance(products, list):
        return []
    return [row for row in products if isinstance(row, dict)]


def sync_gumroad_urls_to_state(
    *,
    access_token: str,
    export_root: Path | None = None,
    products: list[dict[str, Any]] | None = None,
) -> GumroadCatalogSyncResult:
    """Merge Gumroad product URLs + ids into upload tracker state."""

    root = _resolve_export_root(export_root)
    state_path = root / "gumroad-upload-status.json"
    slug_index = _catalog_slug_index(root)
    if not slug_index:
        return GumroadCatalogSyncResult(
            ok=False,
            message="No gumroad-ready catalog manifests found to match.",
            state_path=str(state_path),
        )

    api_rows = products if products is not None else []
    state = _load_upload_state(state_path)
    products_block = state.setdefault("products", {})
    if not isinstance(products_block, dict):
        products_block = {}
        state["products"] = products_block

    synced = 0
    skipped = 0
    for row in api_rows:
        slug = match_gumroad_product_to_slug(row, slug_index)
        if slug is None:
            skipped += 1
            continue
        product_id = str(row.get("id") or row.get("product_id") or "").strip()
        url = str(row.get("short_url") or row.get("url") or "").strip()
        record = dict(products_block.get(slug)) if isinstance(products_block.get(slug), dict) else {}
        record["status"] = "uploaded"
        if url:
            record["gumroad_url"] = url
        if product_id:
            record["gumroad_product_id"] = product_id
        record["synced_at"] = datetime.now(tz=UTC).isoformat()
        products_block[slug] = record
        synced += 1

    state["last_sync_at"] = datetime.now(tz=UTC).isoformat()
    _save_upload_state(state_path, state)
    logger.info(
        "gumroad_catalog_sync_complete",
        synced_count=synced,
        skipped_count=skipped,
        api_product_count=len(api_rows),
        state_path=str(state_path),
    )
    return GumroadCatalogSyncResult(
        ok=True,
        synced_count=synced,
        skipped_count=skipped,
        api_product_count=len(api_rows),
        message=f"Synced {synced} Gumroad URLs into upload tracker.",
        state_path=str(state_path),
    )


async def sync_gumroad_catalog_from_token(
    *,
    access_token: str,
    export_root: Path | None = None,
) -> GumroadCatalogSyncResult:
    """Fetch Gumroad products and persist URL mapping."""

    token = access_token.strip()
    if not token:
        return GumroadCatalogSyncResult(ok=False, message="Gumroad access token missing.")
    try:
        rows = await fetch_gumroad_products(access_token=token)
    except httpx.HTTPError as exc:
        logger.warning("gumroad_catalog_sync_api_failed", error=str(exc))
        return GumroadCatalogSyncResult(ok=False, message="Gumroad API request failed.")
    return sync_gumroad_urls_to_state(access_token=token, export_root=export_root, products=rows)


async def sync_gumroad_catalog_from_settings(
    *,
    connector_secrets: dict[str, Any] | None = None,
    export_root: Path | None = None,
) -> GumroadCatalogSyncResult:
    """Resolve token from connector secrets or settings, then sync."""

    secrets = connector_secrets or {}
    token = _resolve_gumroad_token(secrets)
    return await sync_gumroad_catalog_from_token(access_token=token, export_root=export_root)


def resolve_slug_for_gumroad_product_id(
    product_id: str,
    *,
    export_root: Path | None = None,
) -> str | None:
    """Reverse lookup catalog slug from stored gumroad_product_id."""

    needle = product_id.strip()
    if not needle:
        return None
    root = _resolve_export_root(export_root)
    state = _load_upload_state(root / "gumroad-upload-status.json")
    products = state.get("products")
    if not isinstance(products, dict):
        return None
    for slug, row in products.items():
        if not isinstance(row, dict):
            continue
        stored = str(row.get("gumroad_product_id") or row.get("product_id") or "").strip()
        if stored == needle:
            return str(slug)
    return None


__all__ = [
    "GumroadCatalogSyncResult",
    "fetch_gumroad_products",
    "match_gumroad_product_to_slug",
    "resolve_slug_for_gumroad_product_id",
    "sync_gumroad_catalog_from_settings",
    "sync_gumroad_catalog_from_token",
    "sync_gumroad_urls_to_state",
]
