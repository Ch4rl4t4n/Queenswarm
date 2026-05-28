"""Regression guard against deprecated FastAPI 422 constant usage."""

from __future__ import annotations

from pathlib import Path


_DEPRECATED_422 = "HTTP_422_UNPROCESSABLE_ENTITY"
_RAW_422_STATUS_CODE = "status_code=422"


def _backend_app_root() -> Path:
    """Resolve backend/app root regardless of host vs container path layout."""

    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / "app"
        if candidate.is_dir() and (candidate / "presentation").is_dir():
            return candidate
    raise AssertionError("Could not resolve backend/app root for deprecated-constant guard test.")


def test_backend_app_uses_only_http_422_unprocessable_content_constant() -> None:
    """Prevent reintroducing deprecated HTTP_422_UNPROCESSABLE_ENTITY in app code."""

    app_root = _backend_app_root()
    offenders: list[str] = []
    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _DEPRECATED_422 in text:
            offenders.append(str(path.relative_to(app_root.parent)))
    assert not offenders, (
        "Deprecated HTTP status constant detected. "
        "Use status.HTTP_422_UNPROCESSABLE_CONTENT instead. "
        f"Offenders: {', '.join(offenders)}"
    )


def test_backend_app_does_not_use_raw_numeric_422_status_code() -> None:
    """Prevent raw numeric 422 codes so status constant semantics stay explicit."""

    app_root = _backend_app_root()
    offenders: list[str] = []
    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").replace(" ", "")
        if _RAW_422_STATUS_CODE in text:
            offenders.append(str(path.relative_to(app_root.parent)))
    assert not offenders, (
        "Raw status_code=422 detected. "
        "Use status.HTTP_422_UNPROCESSABLE_CONTENT instead. "
        f"Offenders: {', '.join(offenders)}"
    )
