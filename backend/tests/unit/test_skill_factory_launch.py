"""Unit tests for launch batch preparation service."""

from __future__ import annotations

import tarfile

from app.application.services.skill_factory_launch import LaunchPrepareOut, package_launch_skill_dir


def test_launch_prepare_out_fields_for_fe() -> None:
    fields = set(LaunchPrepareOut.model_fields.keys())
    assert {
        "exported_count",
        "sellable_recommended",
        "tier_counts",
        "checklist_md",
        "exports",
        "message",
    } <= fields


def test_package_launch_skill_dir_creates_uploadable_tarball(tmp_path) -> None:
    skill_dir = tmp_path / "seo-pack"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: seo-pack\n---\n", encoding="utf-8")
    (skill_dir / "LISTING.md").write_text("# Listing\n", encoding="utf-8")

    bundle_path = package_launch_skill_dir(skill_dir)

    assert bundle_path == tmp_path / "seo-pack.tar.gz"
    assert bundle_path.is_file()
    with tarfile.open(bundle_path, "r:gz") as tar:
        names = sorted(member.name for member in tar.getmembers() if member.isfile())
    assert names == ["seo-pack/LISTING.md", "seo-pack/SKILL.md"]
