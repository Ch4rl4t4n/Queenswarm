#!/usr/bin/env python3
"""Phase 2.8 — move backend packages to layered layout and rewrite imports.

Run from repo root: ``python backend/scripts/phase28_migrate_layout.py``
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP = BACKEND_ROOT / "app"


def move_tree(src: Path, dst: Path) -> None:
    """Move directory ``src`` to ``dst`` (creates parent dirs)."""

    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def rewrite_file(path: Path, rules: list[tuple[str, str]]) -> None:
    """Apply ordered substring replacements."""

    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new in rules:
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding="utf-8")


def collect_py_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if ".venv" not in str(p)]


def main() -> None:
    """Execute moves then global import rewrites."""

    # --- A: Cost governor → core (before agents move)
    cg_src = APP / "agents" / "cost_governor.py"
    cg_dst = APP / "core" / "cost_governor.py"
    if cg_src.exists():
        shutil.move(str(cg_src), str(cg_dst))

    pre_rules: list[tuple[str, str]] = [
        ("from app.core.cost_governor import", "from app.core.cost_governor import"),
        ("from app.core import cost_governor", "from app.core import cost_governor"),
    ]
    for py in collect_py_files(BACKEND_ROOT):
        rewrite_file(py, pre_rules)

    agents_init = APP / "agents" / "__init__.py"
    if agents_init.exists():
        rewrite_file(
            agents_init,
            [
                ("from app.core.cost_governor import", "from app.core.cost_governor import"),
            ],
        )

    # --- B: Physical moves (only if source exists and dest missing)
    moves: list[tuple[str, str]] = [
        ("models", "infrastructure/persistence/models"),
        ("schemas", "common/schemas"),
        ("services", "application/services"),
        ("agents", "domain/agents"),
        ("hive_mind", "domain/hive_mind"),
        ("outputs", "domain/outputs"),
        ("external", "domain/external"),
        ("workflows", "domain/workflows"),
        ("recipes", "domain/recipes"),
        ("learning", "domain/learning"),
        ("connectors", "infrastructure/connectors"),
        ("plugins", "infrastructure/plugins"),
        ("api", "presentation/api"),
    ]

    for rel_src, rel_dst in moves:
        src = APP / rel_src
        dst = APP / rel_dst
        if src.exists() and not dst.exists():
            move_tree(src, dst)

    # --- C: Import rewires (order: longest / specific prefixes first)
    rules: list[tuple[str, str]] = [
        ("from app.infrastructure.persistence.models import", "from app.infrastructure.persistence.models import"),
        ("from app.infrastructure.persistence.models.", "from app.infrastructure.persistence.models."),
        ("from app.common.schemas.", "from app.common.schemas."),
        ("from app.application.services.", "from app.application.services."),
        ("from app.domain.agents.", "from app.domain.agents."),
        ("from app.domain.hive_mind.", "from app.domain.hive_mind."),
        ("from app.domain.outputs.", "from app.domain.outputs."),
        ("from app.domain.external.", "from app.domain.external."),
        ("from app.domain.workflows.", "from app.domain.workflows."),
        ("from app.domain.recipes.", "from app.domain.recipes."),
        ("from app.domain.learning.", "from app.domain.learning."),
        ("from app.infrastructure.connectors.", "from app.infrastructure.connectors."),
        ("from app.infrastructure.plugins.", "from app.infrastructure.plugins."),
        ("from app.presentation.api.", "from app.presentation.api."),
        ("import app.models\n", "import app.infrastructure.persistence.models\n"),
        ("import app.infrastructure.persistence.models ", "import app.infrastructure.persistence.models "),
    ]

    # Fix models package lazy-loader string paths inside __init__.py
    models_init = APP / "infrastructure" / "persistence" / "models" / "__init__.py"
    if models_init.exists():
        mi = models_init.read_text(encoding="utf-8")
        mi = mi.replace('"app.models.', '"app.infrastructure.persistence.models.')
        mi = mi.replace("'app.models.", "'app.infrastructure.persistence.models.")
        models_init.write_text(mi, encoding="utf-8")

    for py in collect_py_files(BACKEND_ROOT):
        rewrite_file(py, rules)

    print("Phase 2.8 migrate: moves + import rewrite complete.")


if __name__ == "__main__":
    main()
