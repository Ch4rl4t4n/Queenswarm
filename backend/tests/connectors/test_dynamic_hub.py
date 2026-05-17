"""Phase 1.2 Dynamic Connector Hub unit coverage (vault + manifests + prioritisation helpers)."""

from __future__ import annotations

from app.domain.agents.executor import prioritize_research_connector_tools
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub, manifest_tool_default
from app.infrastructure.connectors.dynamic.models import DynamicConnectorCacheRow
from app.infrastructure.connectors.secure_vault import seal_dynamic_connector_blob, unseal_dynamic_connector_blob


def test_prioritize_research_moves_wikipedia_after_search_stack() -> None:
    bundle = [{"name": "wikipedia", "args": {"topic": "Honey bee"}}]

    prioritized = prioritize_research_connector_tools(
        bundle,
        manager_slug="research_intelligence",
        allowlist_tokens=frozenset({"grokipedia"}),
        agent_name="bee",
        oc={},
    )

    lowered = [str(entry.get("name")).lower() for entry in prioritized if isinstance(entry, dict)]
    assert lowered[0] == "grokipedia"
    assert "serper_search" in lowered
    assert "tavily_search" in lowered
    assert lowered[-1] == "wikipedia"


def test_snapshots_filtered_by_allowlist_star() -> None:
    snapshots = (
        DynamicConnectorCacheRow(
            slug="demo",
            display_name="demo",
            base_url="https://example.com",
            auth_type="api_key",
            mcp_manifest={"tools": [{"name": "invoke"}]},
            allowed_manager_slugs=(),
            is_active=True,
            is_builtin=False,
            builtin_kind=None,
        ),
    )

    routed = DynamicConnectorHub.slugs_available_for_manager(snapshots, manager_slug="execution_operations")
    assert routed == ("demo",)


def test_snapshots_filtered_by_explicit_manager_list() -> None:
    snaps = (
        DynamicConnectorCacheRow(
            slug="cust",
            display_name="custom",
            base_url=None,
            auth_type="none",
            mcp_manifest=None,
            allowed_manager_slugs=("research_intelligence",),
            is_active=True,
            is_builtin=False,
            builtin_kind=None,
        ),
    )
    assert DynamicConnectorHub.slugs_available_for_manager(snaps, manager_slug="research_intelligence") == ("cust",)
    assert DynamicConnectorHub.slugs_available_for_manager(snaps, manager_slug="content_creation") == ()


def test_manifest_default_contains_invoke_tool() -> None:
    payload = manifest_tool_default()
    assert payload["tools"]
    assert payload["tools"][0]["name"] == "invoke"


def test_dynamic_secrets_roundtrip_sealed_blob() -> None:
    corpus = {"api_key": "unit-test-placeholder", "api_key_header_name": "Authorization"}
    cipher = seal_dynamic_connector_blob(corpus)
    reopened = unseal_dynamic_connector_blob(cipher)
    assert reopened["api_key"] == "unit-test-placeholder"
    assert reopened["api_key_header_name"] == "Authorization"
