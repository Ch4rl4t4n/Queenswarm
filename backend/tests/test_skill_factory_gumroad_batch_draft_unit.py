"""Unit tests for Skill Factory Gumroad batch draft planning."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from scripts.skill_factory_gumroad_batch_draft import existing_gumroad_listing_ref, plan_draft_candidates


def _valid_skill_body(name: str) -> str:
    return f"""---
name: {name}
description: Use when operators need a verified launch workflow. NOT for unverified publishing.
---

# {name}

## Workflow

### Step 1: Research demand
Gather niche evidence and save sources.

### Step 2: Draft artifact
Create the reusable workflow file.

### Step 3: Simulate outcome
Run a dry-run verification.

### Step 4: Critic review
Check quality and safety.

### Step 5: Package launch
Prepare the Gumroad bundle.

## Guardrails

- simulate-first: required
- no-secrets: required
- approval-gate: required

## Evaluation

- Workflow has verified output.
- Listing copy is concrete.
- Operator can run it without custom code.
"""


def _skill(*, slug: str, title: str, verified: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        slug=slug,
        title=title,
        description="A launch-ready Skill Factory product.",
        markdown_body=_valid_skill_body(slug),
        verified_at=datetime.now(tz=UTC) if verified else None,
    )


def test_existing_gumroad_listing_ref_detects_any_stored_product() -> None:
    opportunity = SimpleNamespace(
        source_refs=[
            {"kind": "github_pr", "url": "https://example.test/pr"},
            {"kind": "gumroad_listing", "product_id": "prod_123", "published": False},
        ],
    )

    assert existing_gumroad_listing_ref(opportunity)["product_id"] == "prod_123"


def test_plan_draft_candidates_skips_already_linked_gumroad_products() -> None:
    ready = _skill(slug="newsletter-growth", title="Newsletter Growth")
    linked = _skill(slug="seo-pipeline", title="SEO Pipeline")
    opportunities = {
        linked.id: SimpleNamespace(
            tenant_skill_id=linked.id,
            source_refs=[{"kind": "gumroad_listing", "product_id": "prod_existing"}],
        ),
    }

    candidates = plan_draft_candidates(
        [linked, ready],
        opportunities_by_skill_id=opportunities,
        forge_quality_by_skill_id={},
        limit=5,
    )

    assert [candidate.skill.slug for candidate in candidates] == ["newsletter-growth"]


def test_plan_draft_candidates_orders_by_launch_score_then_title() -> None:
    zeta = _skill(slug="zeta-growth", title="Zeta Growth")
    alpha = _skill(slug="alpha-growth", title="Alpha Growth")

    candidates = plan_draft_candidates(
        [zeta, alpha],
        opportunities_by_skill_id={},
        forge_quality_by_skill_id={},
        limit=5,
    )

    assert [candidate.skill.title for candidate in candidates] == ["Alpha Growth", "Zeta Growth"]
