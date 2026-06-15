"""Pydantic row models for forager structured extract (DG2)."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ExtractSchemaKind = Literal[
    "jobs",
    "prices",
    "events",
    "listings",
    "news",
    "repos",
    "social_intel",
    "general",
]

STRUCTURED_EXTRACT_MARKER = "---structured-extract---"

_SUPPORTED_SCHEMAS: frozenset[str] = frozenset(
    {"jobs", "prices", "events", "listings", "news", "repos", "social_intel", "general"},
)

_PRICE_RE = re.compile(
    r"(?P<currency>EUR|USD|GBP|€|\$|£)\s*(?P<amount>[\d][\d.,]*)|"
    r"(?P<amount2>[\d][\d.,]*)\s*(?P<currency2>EUR|USD|GBP|€|\$|£)",
    flags=re.IGNORECASE,
)
_LOCATION_RE = re.compile(r"(?:location|city|region)\s*:\s*(.+)", flags=re.IGNORECASE)


class JobExtractRow(BaseModel):
    """Structured job posting row."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    employer: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=300)
    compensation: str | None = Field(default=None, max_length=120)
    apply_url: str | None = Field(default=None, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)
    published_at: str | None = Field(default=None, max_length=120)


class PriceExtractRow(BaseModel):
    """Structured price observation row."""

    model_config = ConfigDict(extra="forbid")

    product: str = Field(min_length=1, max_length=500)
    price: str | None = Field(default=None, max_length=120)
    currency: str | None = Field(default=None, max_length=16)
    delta_hint: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2048)
    published_at: str | None = Field(default=None, max_length=120)


class EventExtractRow(BaseModel):
    """Structured event row."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=500)
    date: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=300)
    registration_url: str | None = Field(default=None, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)
    published_at: str | None = Field(default=None, max_length=120)


class ListingExtractRow(BaseModel):
    """Structured marketplace / classified listing row."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    price: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=300)
    attributes: str | None = Field(default=None, max_length=500)
    listing_url: str | None = Field(default=None, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)
    published_at: str | None = Field(default=None, max_length=120)


class GeneralExtractRow(BaseModel):
    """Catch-all structured fact row."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=4000)
    source_url: str | None = Field(default=None, max_length=2048)
    published_at: str | None = Field(default=None, max_length=120)


_SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "jobs": JobExtractRow,
    "prices": PriceExtractRow,
    "events": EventExtractRow,
    "listings": ListingExtractRow,
    "news": GeneralExtractRow,
    "repos": GeneralExtractRow,
    "social_intel": GeneralExtractRow,
    "general": GeneralExtractRow,
}


def normalize_extract_schema(raw: str | None) -> ExtractSchemaKind:
    """Map arbitrary schema string to a supported extract template."""

    key = str(raw or "general").strip().lower()
    if key in _SUPPORTED_SCHEMAS:
        return key  # type: ignore[return-value]
    return "general"


def parse_rss_ingest_metadata(content_text: str) -> dict[str, str]:
    """Parse title, URL, and published lines from RSS ingest body."""

    lines = [line.strip() for line in content_text.splitlines()]
    title = ""
    source_url = ""
    published_at = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.lower().startswith("url:"):
            source_url = line.split(":", 1)[1].strip()
        elif line.lower().startswith("published:"):
            published_at = line.split(":", 1)[1].strip()
    body_start = content_text.find("\n\n")
    summary = content_text[body_start:].strip() if body_start >= 0 else content_text
    return {
        "title": title,
        "source_url": source_url,
        "published_at": published_at,
        "summary": summary[:4000],
    }


def _split_employer_from_title(title: str) -> tuple[str, str | None]:
    """Heuristic employer split from a job title."""

    for sep in (" at ", " — ", " - ", " | "):
        if sep in title:
            left, right = title.split(sep, 1)
            if len(left.strip()) >= 2 and len(right.strip()) >= 2:
                return left.strip(), right.strip()
    return title, None


def _extract_price_fields(text: str) -> tuple[str | None, str | None]:
    """Return price string and currency from free text."""

    match = _PRICE_RE.search(text)
    if not match:
        return None, None
    currency = match.group("currency") or match.group("currency2")
    amount = match.group("amount") or match.group("amount2")
    if not amount:
        return None, currency
    return amount.strip(), (currency or "").strip() or None


def _extract_location(text: str) -> str | None:
    """Parse explicit location line from ingest body."""

    match = _LOCATION_RE.search(text)
    if match:
        return match.group(1).strip()[:300] or None
    return None


def heuristic_structured_row(
    *,
    schema: ExtractSchemaKind,
    content_text: str,
    source_url: str | None,
) -> dict[str, Any]:
    """Build a structured row dict from RSS-style ingest text."""

    meta = parse_rss_ingest_metadata(content_text)
    title = meta["title"] or "Untitled signal"
    url = (source_url or meta["source_url"] or "").strip() or None
    published = meta["published_at"] or None
    summary = meta["summary"]

    if schema == "jobs":
        role, employer = _split_employer_from_title(title)
        return JobExtractRow(
            title=role,
            employer=employer,
            location=_extract_location(content_text),
            apply_url=url,
            source_url=url,
            published_at=published if published != "unknown" else None,
        ).model_dump(mode="json")

    if schema == "prices":
        price, currency = _extract_price_fields(content_text)
        return PriceExtractRow(
            product=title,
            price=price,
            currency=currency,
            source_url=url,
            published_at=published if published != "unknown" else None,
        ).model_dump(mode="json")

    if schema == "events":
        return EventExtractRow(
            name=title,
            date=published if published != "unknown" else None,
            location=_extract_location(content_text),
            registration_url=url,
            source_url=url,
            published_at=published if published != "unknown" else None,
        ).model_dump(mode="json")

    if schema == "listings":
        price, _ = _extract_price_fields(content_text)
        return ListingExtractRow(
            title=title,
            price=price,
            location=_extract_location(content_text),
            listing_url=url,
            source_url=url,
            published_at=published if published != "unknown" else None,
        ).model_dump(mode="json")

    return GeneralExtractRow(
        title=title,
        summary=summary[:4000] if summary else None,
        source_url=url,
        published_at=published if published != "unknown" else None,
    ).model_dump(mode="json")


def embed_structured_payload(content_text: str, structured: dict[str, Any]) -> str:
    """Append canonical JSON block for round-trip structured parse."""

    payload = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    base = content_text.rstrip()
    if STRUCTURED_EXTRACT_MARKER in base:
        base = base.split(STRUCTURED_EXTRACT_MARKER, 1)[0].rstrip()
    return f"{base}\n\n{STRUCTURED_EXTRACT_MARKER}\n{payload}"


def parse_structured_payload(content_text: str) -> dict[str, Any] | None:
    """Extract embedded structured JSON from knowledge content_text."""

    if STRUCTURED_EXTRACT_MARKER not in content_text:
        return None
    _, tail = content_text.split(STRUCTURED_EXTRACT_MARKER, 1)
    raw = tail.strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def validate_structured_row(schema: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Validate structured dict against schema model."""

    model_cls = _SCHEMA_MODELS.get(normalize_extract_schema(schema), GeneralExtractRow)
    try:
        return model_cls.model_validate(data).model_dump(mode="json")
    except Exception:
        return None


__all__ = [
    "EventExtractRow",
    "ExtractSchemaKind",
    "GeneralExtractRow",
    "JobExtractRow",
    "ListingExtractRow",
    "PriceExtractRow",
    "STRUCTURED_EXTRACT_MARKER",
    "embed_structured_payload",
    "heuristic_structured_row",
    "normalize_extract_schema",
    "parse_rss_ingest_metadata",
    "parse_structured_payload",
    "validate_structured_row",
]
