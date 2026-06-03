"""Gumroad multipart file upload + cover attach for Skill Factory exports."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import httpx
import structlog

from app.common.schemas.skill_export import SkillExportFile
from app.core.config import settings

logger = structlog.get_logger(__name__)

_GUMROAD_BASE = "https://api.gumroad.com/v2"


def build_skill_export_zip(files: list[SkillExportFile]) -> tuple[str, bytes]:
    """Zip GitHub pack files for Gumroad deliverable attachment."""

    slug = files[0].path.split("/", 1)[0] if files else "skill-pack"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.writestr(item.path, item.content)
    return f"{slug}-github-pack.zip", buffer.getvalue()


def _extract_product_id(payload: dict[str, Any]) -> str | None:
    product = payload.get("product")
    if isinstance(product, dict):
        product_id = str(product.get("id") or "").strip()
        if product_id:
            return product_id
    return None


async def _gumroad_post_form(
    client: httpx.AsyncClient,
    *,
    token: str,
    path: str,
    fields: list[tuple[str, str]],
) -> tuple[int, dict[str, Any], str]:
    """POST form-urlencoded to Gumroad API."""

    body = list(fields)
    body.insert(0, ("access_token", token))
    rsp = await client.post(f"{_GUMROAD_BASE}{path}", data=body)
    try:
        payload = rsp.json()
    except json.JSONDecodeError:
        payload = {}
    return rsp.status_code, payload if isinstance(payload, dict) else {}, rsp.text[:800]


async def upload_bytes_to_gumroad(
    client: httpx.AsyncClient,
    *,
    token: str,
    filename: str,
    content: bytes,
) -> str | None:
    """Presign → S3 PUT → complete; return canonical file_url."""

    status, presign, _raw = await _gumroad_post_form(
        client,
        token=token,
        path="/files/presign",
        fields=[
            ("filename", filename),
            ("file_size", str(len(content))),
        ],
    )
    if status >= 400 or not presign.get("success"):
        logger.warning(
            "skill_factory.gumroad_presign_failed",
            agent_id="skill_factory",
            status=status,
        )
        return None

    upload_id = str(presign.get("upload_id") or "").strip()
    key = str(presign.get("key") or "").strip()
    file_url = str(presign.get("file_url") or "").strip()
    parts = presign.get("parts") if isinstance(presign.get("parts"), list) else []
    if not upload_id or not key or not parts:
        return None

    completed_parts: list[tuple[str, str]] = []
    part_size = 100 * 1024 * 1024
    for part in parts:
        if not isinstance(part, dict):
            continue
        part_number_raw = part.get("part_number")
        presigned_url = str(part.get("presigned_url") or "").strip()
        if part_number_raw is None or not presigned_url:
            continue
        part_number = int(part_number_raw)
        start = (part_number - 1) * part_size
        chunk = content[start : start + part_size]
        put_rsp = await client.put(presigned_url, content=chunk)
        if put_rsp.status_code >= 400:
            logger.warning(
                "skill_factory.gumroad_s3_put_failed",
                agent_id="skill_factory",
                status=put_rsp.status_code,
            )
            return None
        etag = str(put_rsp.headers.get("etag") or "").strip().strip('"')
        completed_parts.append((str(part_number), etag))

    complete_fields: list[tuple[str, str]] = [
        ("upload_id", upload_id),
        ("key", key),
    ]
    for part_number, etag in completed_parts:
        complete_fields.append(("parts[][part_number]", part_number))
        complete_fields.append(("parts[][etag]", etag))

    status, complete_payload, _raw = await _gumroad_post_form(
        client,
        token=token,
        path="/files/complete",
        fields=complete_fields,
    )
    if status >= 400 or not complete_payload.get("success"):
        logger.warning(
            "skill_factory.gumroad_complete_failed",
            agent_id="skill_factory",
            status=status,
        )
        return None

    final_url = str(complete_payload.get("file_url") or file_url).strip()
    return final_url or None


async def attach_file_to_gumroad_product(
    client: httpx.AsyncClient,
    *,
    token: str,
    product_id: str,
    file_url: str,
    display_name: str,
) -> bool:
    """Attach uploaded file URL to existing Gumroad product."""

    status, payload, _raw = await _gumroad_post_form(
        client,
        token=token,
        path=f"/products/{product_id}",
        fields=[
            ("files[][url]", file_url),
            ("files[][display_name]", display_name[:120]),
        ],
    )
    if status < 400 and payload.get("success"):
        return True

    rsp = await client.put(
        f"{_GUMROAD_BASE}/products/{product_id}",
        data={
            "access_token": token,
            "files[][url]": file_url,
            "files[][display_name]": display_name[:120],
        },
    )
    try:
        payload = rsp.json()
    except json.JSONDecodeError:
        payload = {}
    if rsp.status_code >= 400 or not payload.get("success"):
            logger.warning(
                "skill_factory.gumroad_attach_failed",
                agent_id="skill_factory",
                status=rsp.status_code,
            )
            return False
    return True


async def attach_cover_to_gumroad_product(
    client: httpx.AsyncClient,
    *,
    token: str,
    product_id: str,
    cover_url: str,
) -> bool:
    """Attach cover/preview from public URL (video or image)."""

    status, payload, _raw = await _gumroad_post_form(
        client,
        token=token,
        path=f"/products/{product_id}/covers",
        fields=[("url", cover_url)],
    )
    if status >= 400 or not payload.get("success"):
        logger.warning(
            "skill_factory.gumroad_cover_failed",
            agent_id="skill_factory",
            status=status,
        )
        return False
    return True


async def enrich_gumroad_product_assets(
    *,
    token: str,
    product_id: str,
    bundle_files: list[SkillExportFile],
    cover_preview_url: str | None,
) -> dict[str, Any]:
    """Upload zip deliverable + optional preview cover after draft product create."""

    result: dict[str, Any] = {"product_id": product_id}
    if not settings.skill_factory_gumroad_attach_bundle_enabled and not (
        settings.skill_factory_gumroad_cover_from_preview_enabled and cover_preview_url
    ):
        result["skipped"] = True
        return result

    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if settings.skill_factory_gumroad_attach_bundle_enabled and bundle_files:
            zip_name, zip_bytes = build_skill_export_zip(bundle_files)
            file_url = await upload_bytes_to_gumroad(client, token=token, filename=zip_name, content=zip_bytes)
            if file_url:
                attached = await attach_file_to_gumroad_product(
                    client,
                    token=token,
                    product_id=product_id,
                    file_url=file_url,
                    display_name=zip_name,
                )
                result["bundle_attached"] = attached
                result["bundle_file_url"] = file_url[:200]
            else:
                result["bundle_attached"] = False

        if settings.skill_factory_gumroad_cover_from_preview_enabled and cover_preview_url:
            result["cover_attached"] = await attach_cover_to_gumroad_product(
                client,
                token=token,
                product_id=product_id,
                cover_url=cover_preview_url,
            )

    return result


__all__ = [
    "attach_cover_to_gumroad_product",
    "attach_file_to_gumroad_product",
    "build_skill_export_zip",
    "enrich_gumroad_product_assets",
    "upload_bytes_to_gumroad",
    "_extract_product_id",
]
