from __future__ import annotations

import io
import tarfile
from pathlib import Path

from scripts.gumroad_upload_shortlist import build_shortlist, render_markdown


def _write_tar(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def test_build_shortlist_prioritizes_content_packs_and_skips_drafts(tmp_path: Path) -> None:
    _write_tar(
        tmp_path / "facebook-local-pack.tar.gz",
        {
            "facebook-local-pack/LISTING.md": "\n".join(
                [
                    "# LISTING.md",
                    "**Hook:** Book more local-service jobs with proven Facebook ads.",
                    "",
                    "**Target buyer:** Local service owners.",
                    "",
                    "**Price:** EUR 19.00",
                ],
            ),
        },
    )
    _write_tar(
        tmp_path / "crypto-sentiment-alerts.tar.gz",
        {
            "./LISTING.md": "\n".join(
                [
                    "# LISTING.md",
                    "## One-line hook (Gumroad subtitle)",
                    "Real-time sentiment alerts for top crypto assets.",
                    "",
                    "## Price anchor",
                    "EUR 19.00",
                    "",
                    "## Short description",
                    "Alerts for crypto operators.",
                ],
            ),
        },
    )
    _write_tar(
        tmp_path / "skill-factory-draft.tar.gz",
        {"./LISTING.md": "# LISTING.md\n\nDraft from Skill Factory session — review before publish\n"},
    )

    rows = build_shortlist(tmp_path, limit=10)

    assert [row["slug"] for row in rows] == ["facebook-local-pack", "crypto-sentiment-alerts"]
    assert rows[0]["kind"] == "content_pack"
    assert rows[0]["score"] > rows[1]["score"]


def test_build_shortlist_can_include_drafts_when_requested(tmp_path: Path) -> None:
    _write_tar(
        tmp_path / "skill-factory-draft.tar.gz",
        {"./LISTING.md": "# LISTING.md\n\nDraft from Skill Factory session — review before publish\n"},
    )

    rows = build_shortlist(tmp_path, limit=10, include_drafts=True)

    assert rows[0]["slug"] == "skill-factory-draft"
    assert rows[0]["kind"] == "skill_factory_draft"


def test_build_shortlist_cleans_markdown_bold_from_skill_price(tmp_path: Path) -> None:
    _write_tar(
        tmp_path / "crypto-sentiment-alerts.tar.gz",
        {
            "./LISTING.md": "\n".join(
                [
                    "# LISTING.md",
                    "## One-line hook (Gumroad subtitle)",
                    "Real-time sentiment alerts.",
                    "",
                    "## Price anchor",
                    "€19.00** — suggested tiers: €10 starter / €19 pro / €28 team",
                    "",
                    "## Short description",
                    "Alerts for crypto operators.",
                ],
            ),
        },
    )

    rows = build_shortlist(tmp_path, limit=10)

    assert rows[0]["price"] == "€19.00 — suggested tiers: €10 starter / €19 pro / €28 team"


def test_render_markdown_creates_operator_upload_checklist() -> None:
    markdown = render_markdown(
        [
            {
                "slug": "facebook-local-pack",
                "kind": "content_pack",
                "score": 115,
                "subtitle": "Book more local-service jobs.",
                "price": "EUR 19.00",
                "description": "Local service owners.",
                "bundle": "/tmp/facebook-local-pack.tar.gz",
                "listing_path": "facebook-local-pack/LISTING.md",
            },
        ],
    )

    assert "# Gumroad Upload Shortlist" in markdown
    assert "- [ ] `facebook-local-pack` (content_pack, score 115)" in markdown
    assert "**Price:** EUR 19.00" in markdown
    assert "`/tmp/facebook-local-pack.tar.gz`" in markdown
