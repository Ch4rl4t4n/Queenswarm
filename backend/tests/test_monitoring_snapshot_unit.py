"""Host metrics slice for operator monitoring (no DB)."""

from __future__ import annotations

from app.application.services.monitoring_snapshot import _docker_running_sync, _host_metrics_sync


def test_host_metrics_sync_returns_core_fields() -> None:
    """CPU/RAM/swap/disk keys must stay stable for dashboard contracts."""

    payload = _host_metrics_sync()
    for key in (
        "cpu_percent",
        "memory_percent",
        "memory_used_bytes",
        "memory_total_bytes",
        "swap_percent",
        "swap_used_bytes",
        "swap_total_bytes",
        "disk_percent",
        "disk_used_bytes",
        "disk_total_bytes",
    ):
        assert key in payload
    assert isinstance(payload["cpu_percent"], float)


def test_docker_running_sync_never_raises() -> None:
    """Without Docker socket the helper degrades to unavailable flag."""

    count, unavailable = _docker_running_sync()
    assert unavailable is True or isinstance(count, int)
