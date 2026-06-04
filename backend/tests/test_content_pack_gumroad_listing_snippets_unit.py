from __future__ import annotations

import io
import tarfile
from pathlib import Path

from scripts.content_pack_gumroad_listing_snippets import (
    extract_listing_fields,
    iter_content_pack_bundles,
)


def _write_bundle(path: Path, *, slug: str, listing: str) -> None:
    with tarfile.open(path, "w:gz") as tar:
        data = listing.encode("utf-8")
        info = tarfile.TarInfo(f"{slug}/LISTING.md")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def test_iter_content_pack_bundles_reads_listing_from_tarball(tmp_path: Path) -> None:
    bundle = tmp_path / "facebook-local-pack.tar.gz"
    _write_bundle(
        bundle,
        slug="facebook-local-pack",
        listing="# LISTING.md\n\n## One-line hook\nFacebook ads for local services.\n\n## Price anchor\nEUR 19\n",
    )

    rows = list(iter_content_pack_bundles(tmp_path))

    assert rows == [
        {
            "slug": "facebook-local-pack",
            "bundle": str(bundle),
            "listing_path": "facebook-local-pack/LISTING.md",
            "subtitle": "Facebook ads for local services.",
            "price": "EUR 19",
            "description": "",
        },
    ]


def test_iter_content_pack_bundles_skips_skill_factory_root_listing(tmp_path: Path) -> None:
    bundle = tmp_path / "skill-factory-draft.tar.gz"
    with tarfile.open(bundle, "w:gz") as tar:
        data = b"# LISTING.md\n\nSkill Factory export\n"
        info = tarfile.TarInfo("./LISTING.md")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    assert list(iter_content_pack_bundles(tmp_path)) == []


def test_extract_listing_fields_accepts_title_fallback() -> None:
    fields = extract_listing_fields("# LISTING.md\n\nCalm brand voice kit for wellness creators.\n")

    assert fields["subtitle"] == "Calm brand voice kit for wellness creators."
    assert fields["price"] == ""


def test_extract_listing_fields_accepts_bold_label_format() -> None:
    fields = extract_listing_fields(
        "\n".join(
            [
                "# LISTING.md",
                "**Title:** Facebook ad copy variations",
                "",
                "**Hook:** Stop guessing your Facebook ad copy.",
                "",
                "**Target buyer:** Local service owners who need better lead ads.",
                "",
                "**Price:** EUR 19.00",
            ],
        ),
    )

    assert fields["subtitle"] == "Stop guessing your Facebook ad copy."
    assert fields["description"] == "Local service owners who need better lead ads."
    assert fields["price"] == "EUR 19.00"


def test_extract_listing_fields_accepts_bold_price_anchor_label() -> None:
    fields = extract_listing_fields(
        "\n".join(
            [
                "# LISTING.md",
                "**Hook:** Stop staring at a blank Instagram grid.",
                "",
                "**Target buyer:** Coaches who need predictable content.",
                "",
                "**Price anchor:** €9.00",
            ],
        ),
    )

    assert fields["price"] == "€9.00"
