"""Unit tests for Gumroad ready-to-upload package assembly."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

from scripts.gumroad_ready_package import build_ready_packages
from scripts.gumroad_upload_tracker import parse_shortlist


def _write_tar(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def test_build_ready_packages_writes_upload_directory_for_next_product(tmp_path: Path) -> None:
    bundle = tmp_path / "seo-pack.tar.gz"
    _write_tar(
        bundle,
        {
            "seo-pack/LISTING.md": "\n".join(
                [
                    "# LISTING.md",
                    "",
                    "**Title:** SEO Repurpose Pack",
                    "",
                    "**Hook:** Turn one blog post into a full week of useful social snippets.",
                ],
            ),
        },
    )
    products = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `seo-pack` (content_pack, score 115)
  - **Subtitle:** Turn one blog post into many useful social snippets for agencies.
  - **Price:** EUR 19.00
  - **Description:** SEO agencies that need faster social repurposing.
  - **File:** `{bundle}`
  - **Listing:** `seo-pack/LISTING.md`
""",
    )

    written = build_ready_packages(tmp_path / "ready", products, state={"products": {}})

    assert [path.name for path in written] == ["seo-pack"]
    package_dir = tmp_path / "ready" / "seo-pack"
    assert (package_dir / "product-bundle.tar.gz").is_file()
    assert (package_dir / "GUMROAD_FIELDS.md").is_file()
    assert (package_dir / "cover.html").is_file()
    assert (package_dir / "COVER_BRIEF.md").is_file()
    assert (package_dir / "README.md").is_file()
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["slug"] == "seo-pack"
    assert manifest["price"] == "EUR 19.00"
    assert manifest["bundle_file"] == "product-bundle.tar.gz"
    queue = (tmp_path / "ready" / "UPLOAD_QUEUE.md").read_text(encoding="utf-8")
    assert "1. `seo-pack`" in queue
    assert "GUMROAD_FIELDS.md" in queue
    assert "product-bundle.tar.gz" in queue


def test_build_ready_packages_all_skips_uploaded_and_qa_blocked(tmp_path: Path) -> None:
    first_bundle = tmp_path / "first.tar.gz"
    second_bundle = tmp_path / "second.tar.gz"
    _write_tar(first_bundle, {"first/LISTING.md": "# LISTING.md\n\n**Hook:** First launch hook.\n"})
    _write_tar(second_bundle, {"second/LISTING.md": "# LISTING.md\n\n**Hook:** Second launch hook.\n"})
    products = parse_shortlist(
        f"""# Gumroad Upload Shortlist

- [ ] `first` (content_pack, score 115)
  - **Subtitle:** A strong Gumroad subtitle for first product.
  - **Price:** EUR 19.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{first_bundle}`
  - **Listing:** `first/LISTING.md`

- [ ] `second` (content_pack, score 110)
  - **Subtitle:** A strong Gumroad subtitle for second product.
  - **Price:** EUR 29.00
  - **Description:** A concrete target buyer and outcome description.
  - **File:** `{second_bundle}`
  - **Listing:** `second/LISTING.md`

- [ ] `blocked` (content_pack, score 80)
  - **Subtitle:** Too short.
  - **Description:** Weak.
  - **File:** `/tmp/missing.tar.gz`
  - **Listing:** `blocked/LISTING.md`
""",
    )

    written = build_ready_packages(
        tmp_path / "ready",
        products,
        state={"products": {"first": {"status": "uploaded"}}},
        all_products=True,
    )

    assert [path.name for path in written] == ["second"]
    assert not (tmp_path / "ready" / "first").exists()
    assert not (tmp_path / "ready" / "blocked").exists()
    queue = (tmp_path / "ready" / "UPLOAD_QUEUE.md").read_text(encoding="utf-8")
    assert "`second`" in queue
    assert "`first`" not in queue
    assert "`blocked`" not in queue
