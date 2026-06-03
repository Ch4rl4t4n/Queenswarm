"""Unit tests for Gumroad asset upload helpers."""

from __future__ import annotations

import zipfile
from io import BytesIO

from app.application.services.skill_factory_gumroad_assets import build_skill_export_zip
from app.common.schemas.skill_export import SkillExportFile


def test_build_skill_export_zip_contains_files() -> None:
    files = [
        SkillExportFile(path="my-skill/SKILL.md", content="# Skill"),
        SkillExportFile(path="my-skill/LISTING.md", content="# Listing"),
    ]
    name, blob = build_skill_export_zip(files)
    assert name == "my-skill-github-pack.zip"
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        names = archive.namelist()
    assert "my-skill/SKILL.md" in names
    assert "my-skill/LISTING.md" in names
