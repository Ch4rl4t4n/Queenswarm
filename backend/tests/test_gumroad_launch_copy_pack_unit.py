"""Unit tests for Gumroad launch copy pack generation."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from scripts.gumroad_launch_copy_pack import (
    extract_listing_from_bundle,
    prepare_next_launch_product,
    render_launch_copy,
    select_launch_product,
)
from scripts.gumroad_upload_tracker import parse_shortlist


def _write_tar(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def test_select_launch_product_skips_uploaded_and_qa_blocked(tmp_path: Path) -> None:
    good_bundle = tmp_path / "good-pack.tar.gz"
    good_bundle.write_text("placeholder", encoding="utf-8")
    products = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `uploaded-pack` (content_pack, score 115)
  - **Subtitle:** A strong hook for uploaded pack with enough detail.
  - **Price:** EUR 19.00
  - **Description:** A useful description for uploaded pack.
  - **File:** `{good_bundle}`
  - **Listing:** `uploaded-pack/LISTING.md`

- [ ] `blocked-pack` (content_pack, score 110)
  - **Subtitle:** Too short.
  - **Description:** Weak.
  - **File:** `/tmp/missing.tar.gz`
  - **Listing:** `blocked-pack/LISTING.md`

- [ ] `good-pack` (content_pack, score 105)
  - **Subtitle:** A strong Gumroad subtitle for a launch-ready product.
  - **Price:** EUR 29.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{good_bundle}`
  - **Listing:** `good-pack/LISTING.md`
""",
    )
    state = {"products": {"uploaded-pack": {"status": "uploaded"}}}

    selected = select_launch_product(products, state)

    assert selected is not None
    assert selected.slug == "good-pack"


def test_extract_listing_from_bundle_reads_slug_listing(tmp_path: Path) -> None:
    bundle = tmp_path / "good-pack.tar.gz"
    _write_tar(bundle, {"good-pack/LISTING.md": "# LISTING.md\n\n**Hook:** Better launches.\n"})

    listing = extract_listing_from_bundle(bundle, "good-pack/LISTING.md")

    assert listing == "# LISTING.md\n\n**Hook:** Better launches.\n"


def test_render_launch_copy_contains_copy_paste_sections(tmp_path: Path) -> None:
    bundle = tmp_path / "good-pack.tar.gz"
    bundle.write_text("placeholder", encoding="utf-8")
    product = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `good-pack` (content_pack, score 115)
  - **Subtitle:** A strong Gumroad subtitle for a launch-ready product.
  - **Price:** EUR 29.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{bundle}`
  - **Listing:** `good-pack/LISTING.md`
""",
    )[0]

    markdown = render_launch_copy(product, "# LISTING.md\n\n**Hook:** Better launches.\n")

    assert "# Gumroad Launch Copy" in markdown
    assert "## Gumroad Fields" in markdown
    assert "**Title:** good-pack" in markdown
    assert "**Subtitle:** A strong Gumroad subtitle" in markdown
    assert "## Launch Post" in markdown
    assert "Better launches" in markdown


def test_prepare_next_launch_product_marks_uploaded_then_selects_next(tmp_path: Path) -> None:
    bundle = tmp_path / "good-pack.tar.gz"
    bundle.write_text("placeholder", encoding="utf-8")
    products = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `first-pack` (content_pack, score 115)
  - **Subtitle:** A strong Gumroad subtitle for first launch-ready product.
  - **Price:** EUR 19.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{bundle}`
  - **Listing:** `first-pack/LISTING.md`

- [ ] `second-pack` (content_pack, score 110)
  - **Subtitle:** A strong Gumroad subtitle for second launch-ready product.
  - **Price:** EUR 29.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{bundle}`
  - **Listing:** `second-pack/LISTING.md`
""",
    )

    selected, state = prepare_next_launch_product(
        products,
        {"products": {}},
        mark_uploaded_slug="first-pack",
        gumroad_url="https://gum.co/first",
    )

    assert selected is not None
    assert selected.slug == "second-pack"
    assert state["products"]["first-pack"]["status"] == "uploaded"
    assert state["products"]["first-pack"]["gumroad_url"] == "https://gum.co/first"
