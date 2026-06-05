"""Public product catalog for letagentscook.org — sourced from gumroad-ready manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

FEATURED_SLUGS: tuple[str, ...] = (
    "newsletter-growth-loop-with-verified-outcomes-5",
    "seo-content-pipeline-with-simulate-first-guardrails-7",
    "30-day-instagram-content-calendar-for-coaches-simulate-first-pack",
)

def _repo_exports_root() -> Path:
    """Repo ``exports/`` directory (works in dev without Docker bind mounts)."""

    return Path(__file__).resolve().parents[4] / "exports"


DEFAULT_EXPORT_ROOTS: tuple[Path, ...] = (
    Path("exports"),
    _repo_exports_root(),
    Path("/exports"),
    Path("/app/exports"),
)


class MarketingProductOut(BaseModel):
    """One sellable skill or content pack for the marketing site."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    kind: str
    title: str
    subtitle: str
    price: str
    score: int
    featured: bool = False
    gumroad_url: str | None = None
    package_dir: str | None = None


class MarketingCatalogOut(BaseModel):
    """Full public catalog payload."""

    model_config = ConfigDict(extra="ignore")

    generated_from: str
    product_count: int
    featured_slugs: list[str] = Field(default_factory=list)
    products: list[MarketingProductOut] = Field(default_factory=list)


def _resolve_export_root(export_root: Path | None = None) -> Path:
    """Return the first existing exports root."""

    if export_root is not None:
        return export_root.expanduser().resolve()
    for candidate in DEFAULT_EXPORT_ROOTS:
        resolved = candidate.expanduser().resolve()
        if (resolved / "gumroad-ready").is_dir():
            return resolved
    return Path("exports").resolve()


def _normalize_family_key(slug: str) -> str:
    """Collapse numbered variants into one catalog family key."""

    base = slug.removesuffix("-simulate-first-pack")
    base = re.sub(r"-\d+$", "", base)
    return base


def _parse_gumroad_title(fields_md: str, *, fallback: str) -> str:
    """Extract Gumroad title from GUMROAD_FIELDS.md."""

    for line in fields_md.splitlines():
        clean = line.strip()
        if clean.startswith("**Title:**"):
            return clean.split("**Title:**", 1)[1].strip()
    return fallback


def _humanize_slug(slug: str) -> str:
    """Turn a slug into a readable English title."""

    text = slug.removesuffix("-simulate-first-pack")
    text = re.sub(r"-\d+$", "", text)
    return text.replace("-", " ").strip().title()


def _load_gumroad_urls(export_root: Path) -> dict[str, str]:
    """Load uploaded Gumroad URLs from tracker state."""

    state_path = export_root / "gumroad-upload-status.json"
    if not state_path.is_file():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    products = payload.get("products")
    if not isinstance(products, dict):
        return {}
    urls: dict[str, str] = {}
    for slug, row in products.items():
        if not isinstance(row, dict):
            continue
        url = str(row.get("gumroad_url") or row.get("url") or "").strip()
        if url:
            urls[str(slug)] = url
    return urls


def collect_catalog_products(export_root: Path | None = None) -> list[MarketingProductOut]:
    """Scan gumroad-ready manifests and return deduped catalog rows."""

    root = _resolve_export_root(export_root)
    ready_dir = root / "gumroad-ready"
    if not ready_dir.is_dir():
        return []

    gumroad_urls = _load_gumroad_urls(root)
    best_by_family: dict[str, MarketingProductOut] = {}

    for package_dir in sorted(ready_dir.iterdir()):
        if not package_dir.is_dir():
            continue
        manifest_path = package_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict):
            continue

        slug = str(manifest.get("slug") or package_dir.name).strip()
        if not slug:
            continue
        kind = str(manifest.get("kind") or "skill_factory").strip()
        score = int(manifest.get("score") or 0)
        subtitle = str(manifest.get("subtitle") or manifest.get("description") or "").strip()
        price = str(manifest.get("price") or "").strip()

        fields_path = package_dir / "GUMROAD_FIELDS.md"
        title = _humanize_slug(slug)
        if fields_path.is_file():
            try:
                title = _parse_gumroad_title(fields_path.read_text(encoding="utf-8"), fallback=title)
            except OSError:
                pass
        title = re.sub(r"^Listing\s*—\s*", "", title, flags=re.I).strip()

        family = _normalize_family_key(slug)
        featured_families = {_normalize_family_key(item) for item in FEATURED_SLUGS}
        row = MarketingProductOut(
            slug=slug,
            kind=kind,
            title=title,
            subtitle=subtitle[:280],
            price=price,
            score=score,
            featured=slug in FEATURED_SLUGS or family in featured_families,
            gumroad_url=gumroad_urls.get(slug),
            package_dir=str(package_dir),
        )
        existing = best_by_family.get(family)
        if existing is None or row.score > existing.score:
            best_by_family[family] = row

    products = sorted(
        best_by_family.values(),
        key=lambda item: (-int(item.featured), -item.score, item.title.lower()),
    )
    return products


def build_catalog(export_root: Path | None = None) -> MarketingCatalogOut:
    """Build the full marketing catalog response."""

    root = _resolve_export_root(export_root)
    products = collect_catalog_products(root)
    return MarketingCatalogOut(
        generated_from=str(root / "gumroad-ready"),
        product_count=len(products),
        featured_slugs=[
            product.slug for product in products if product.featured
        ],
        products=products,
    )


def find_product(slug: str, export_root: Path | None = None) -> MarketingProductOut | None:
    """Return one catalog product by slug."""

    for product in collect_catalog_products(export_root):
        if product.slug == slug:
            return product
    return None


__all__ = [
    "FEATURED_SLUGS",
    "MarketingCatalogOut",
    "MarketingProductOut",
    "build_catalog",
    "collect_catalog_products",
    "find_product",
]
