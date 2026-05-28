"""Unit tests for Meta OAuth provider registration and account parsing."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.services.meta_social_context import fetch_meta_page_accounts
from app.application.services.oauth_consent.providers import OAUTH_SURFACES, oauth_catalog_snapshot
from app.application.services.oauth_consent.service import _build_authorize_url


def test_oauth_surfaces_include_meta_instagram_and_facebook() -> None:
    """Hosted consent must expose Instagram and Facebook Graph surfaces."""

    assert "instagram_graph" in OAUTH_SURFACES
    assert "facebook_graph" in OAUTH_SURFACES
    assert "twitter_api_v2" in OAUTH_SURFACES
    assert "tiktok_content" in OAUTH_SURFACES
    assert "linkedin_api" not in OAUTH_SURFACES
    assert OAUTH_SURFACES["instagram_graph"].vendor_family == "meta"
    assert OAUTH_SURFACES["facebook_graph"].vendor_family == "meta"
    assert OAUTH_SURFACES["twitter_api_v2"].vendor_family == "x"
    assert OAUTH_SURFACES["tiktok_content"].vendor_family == "tiktok"
    assert OAUTH_SURFACES["tiktok_content"].uses_pkce is True
    assert OAUTH_SURFACES["twitter_api_v2"].uses_pkce is True


def test_oauth_catalog_marks_x_configured_when_env_present() -> None:
    """Catalog reports x family configured when client id+secret set."""

    settings = SimpleNamespace(
        oauth_redirect_uri="https://queenswarm.love/api/auth/callback/oauth",
        oauth_google_client_id="",
        oauth_google_client_secret="",
        oauth_microsoft_client_id="",
        oauth_microsoft_client_secret="",
        oauth_github_client_id="",
        oauth_github_client_secret="",
        oauth_notion_client_id="",
        oauth_notion_client_secret="",
        oauth_meta_client_id="",
        oauth_meta_client_secret="",
        oauth_x_client_id="x-client",
        oauth_x_client_secret="x-secret",
        oauth_tiktok_client_key="",
        oauth_tiktok_client_secret="",
    )
    snap = oauth_catalog_snapshot(settings)  # type: ignore[arg-type]
    providers = {row["provider_key"]: row for row in snap["providers"]}
    assert providers["twitter_api_v2"]["configured"] is True


def test_meta_authorize_url_includes_config_id_when_set() -> None:
    """Facebook Login for Business apps require config_id on the OAuth dialog URL."""

    spec = OAUTH_SURFACES["instagram_graph"]
    url = _build_authorize_url(
        spec,
        client_id="2051154204833658",
        redirect_uri="https://queenswarm.love/api/auth/callback/oauth",
        state="test-state",
        code_challenge=None,
        nonce="nonce",
        meta_config_id="1234567890",
    )
    assert "config_id=1234567890" in url
    assert "override_default_response_type=true" in url
    assert "instagram_basic" in url
    assert "IG_API_ONBOARDING" not in url


def test_meta_instagram_authorize_url_omits_ig_api_onboarding() -> None:
    """IG_API_ONBOARDING breaks Meta dialog — use plain scope-based OAuth."""

    spec = OAUTH_SURFACES["instagram_graph"]
    url = _build_authorize_url(
        spec,
        client_id="2061184204835658",
        redirect_uri="https://queenswarm.love/api/auth/callback/oauth",
        state="test-state",
        code_challenge=None,
        nonce="nonce",
    )
    assert "IG_API_ONBOARDING" not in url
    assert "public_profile" in url
    assert "instagram_basic" in url
    assert "config_id=" not in url


def test_oauth_catalog_marks_meta_configured_when_env_present() -> None:
    """Catalog reports meta family configured when client id+secret set."""

    settings = SimpleNamespace(
        oauth_redirect_uri="https://queenswarm.love/api/auth/callback/oauth",
        oauth_google_client_id="",
        oauth_google_client_secret="",
        oauth_microsoft_client_id="",
        oauth_microsoft_client_secret="",
        oauth_github_client_id="",
        oauth_github_client_secret="",
        oauth_notion_client_id="",
        oauth_notion_client_secret="",
        oauth_meta_client_id="meta-app-id",
        oauth_meta_client_secret="meta-secret",
        oauth_x_client_id="",
        oauth_x_client_secret="",
        oauth_tiktok_client_key="",
        oauth_tiktok_client_secret="",
    )
    snap = oauth_catalog_snapshot(settings)  # type: ignore[arg-type]
    providers = {row["provider_key"]: row for row in snap["providers"]}
    assert providers["instagram_graph"]["configured"] is True
    assert providers["facebook_graph"]["configured"] is True


@pytest.mark.asyncio
async def test_fetch_meta_page_accounts_parses_ig_business(monkeypatch) -> None:
    """Graph /me/accounts payload maps to MetaPageAccountOut rows."""

    class _Resp:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "data": [
                    {
                        "id": "111",
                        "name": "Queenswarm Page",
                        "instagram_business_account": {"id": "222", "username": "queenswarm"},
                    },
                ],
            }

    class _Client:
        async def __aenter__(self):  # noqa: ANN204
            return self

        async def __aexit__(self, *args):  # noqa: ANN002, ANN204
            return None

        async def get(self, url: str, params: dict):  # noqa: ANN001
            assert "me/accounts" in url
            return _Resp()

    monkeypatch.setattr(
        "app.application.services.meta_social_context.httpx.AsyncClient",
        lambda **kwargs: _Client(),  # noqa: ARG005
    )

    pages = await fetch_meta_page_accounts(access_token="test-token")
    assert len(pages) == 1
    assert pages[0].page_id == "111"
    assert pages[0].ig_user_id == "222"
    assert pages[0].ig_username == "queenswarm"


@pytest.mark.asyncio
async def test_fetch_x_user_profile_parses_username(monkeypatch) -> None:
    """GET /2/users/me maps to user id + username."""

    class _Resp:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {"data": {"id": "999", "username": "queenswarm"}}

    class _Client:
        async def __aenter__(self):  # noqa: ANN204
            return self

        async def __aexit__(self, *args):  # noqa: ANN002, ANN204
            return None

        async def get(self, url: str, headers: dict, params: dict):  # noqa: ANN001
            assert "users/me" in url
            return _Resp()

    monkeypatch.setattr(
        "app.application.services.x_social_context.httpx.AsyncClient",
        lambda **kwargs: _Client(),  # noqa: ARG005
    )

    from app.application.services.x_social_context import fetch_x_user_profile

    user_id, username = await fetch_x_user_profile(access_token="tok")
    assert user_id == "999"
    assert username == "queenswarm"
