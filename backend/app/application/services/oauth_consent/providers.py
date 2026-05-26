"""OAuth provider registry for Phase 3 connector templates (Authorization Code + PKCE where supported)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.config import Settings

VendorFamily = Literal["google", "microsoft", "github", "notion", "stripe", "meta", "x", "tiktok"]


@dataclass(frozen=True)
class OAuthSurfaceSpec:
    """One hosted-consent surface mapped to a Phase 3 template + upstream OAuth endpoints."""

    provider_key: str
    template_id: str
    label: str
    vendor_family: VendorFamily
    authorize_url: str
    token_url: str
    scopes: tuple[str, ...]
    uses_pkce: bool = True
    google_offline_prompt: bool = False
    notion_owner_user: bool = False


OAUTH_SURFACES: dict[str, OAuthSurfaceSpec] = {
    "google_gmail": OAuthSurfaceSpec(
        provider_key="google_gmail",
        template_id="gmail_google_workspace",
        label="Gmail · Google Workspace",
        vendor_family="google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=(
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.modify",
        ),
        google_offline_prompt=True,
    ),
    "google_calendar": OAuthSurfaceSpec(
        provider_key="google_calendar",
        template_id="google_calendar",
        label="Google Calendar",
        vendor_family="google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=(
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/calendar",
        ),
        google_offline_prompt=True,
    ),
    "microsoft_graph": OAuthSurfaceSpec(
        provider_key="microsoft_graph",
        template_id="outlook_microsoft365",
        label="Outlook · Microsoft 365",
        vendor_family="microsoft",
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        scopes=(
            "offline_access",
            "openid",
            "profile",
            "email",
            "User.Read",
            "Mail.ReadWrite",
            "Mail.Send",
        ),
    ),
    "github_rest": OAuthSurfaceSpec(
        provider_key="github_rest",
        template_id="github_rest",
        label="GitHub",
        vendor_family="github",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes=("read:user", "user:email", "repo"),
    ),
    "notion_workspace": OAuthSurfaceSpec(
        provider_key="notion_workspace",
        template_id="notion_workspace",
        label="Notion",
        vendor_family="notion",
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        scopes=(),
        notion_owner_user=True,
    ),
    "stripe_billing": OAuthSurfaceSpec(
        provider_key="stripe_billing",
        template_id="stripe_billing",
        label="Stripe",
        vendor_family="stripe",
        authorize_url="https://connect.stripe.com/oauth/authorize",
        token_url="https://connect.stripe.com/oauth/token",
        scopes=("read_write",),
        uses_pkce=False,
    ),
    "instagram_graph": OAuthSurfaceSpec(
        provider_key="instagram_graph",
        template_id="instagram_graph_api",
        label="Instagram · Meta Graph",
        vendor_family="meta",
        authorize_url="https://www.facebook.com/v22.0/dialog/oauth",
        token_url="https://graph.facebook.com/v22.0/oauth/access_token",
        scopes=(
            "public_profile",
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "pages_read_engagement",
        ),
        uses_pkce=False,
    ),
    "facebook_graph": OAuthSurfaceSpec(
        provider_key="facebook_graph",
        template_id="facebook_graph_api",
        label="Facebook · Meta Graph Pages",
        vendor_family="meta",
        authorize_url="https://www.facebook.com/v22.0/dialog/oauth",
        token_url="https://graph.facebook.com/v22.0/oauth/access_token",
        scopes=(
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
        ),
        uses_pkce=False,
    ),
    "twitter_api_v2": OAuthSurfaceSpec(
        provider_key="twitter_api_v2",
        template_id="twitter_api_v2",
        label="X (Twitter) · API v2",
        vendor_family="x",
        authorize_url="https://twitter.com/i/oauth2/authorize",
        token_url="https://api.twitter.com/2/oauth2/token",
        scopes=("tweet.read", "tweet.write", "users.read", "offline.access"),
        uses_pkce=True,
    ),
    "tiktok_content": OAuthSurfaceSpec(
        provider_key="tiktok_content",
        template_id="tiktok_content_posting",
        label="TikTok · Content Posting API",
        vendor_family="tiktok",
        authorize_url="https://www.tiktok.com/v2/auth/authorize/",
        token_url="https://open.tiktokapis.com/v2/oauth/token/",
        scopes=("user.info.basic", "video.publish"),
        uses_pkce=True,
    ),
}


def _family_configured(settings: Settings, family: VendorFamily) -> bool:
    """Return True when both client id and secret are present for the vendor family."""

    if family == "google":
        return bool(settings.oauth_google_client_id.strip() and settings.oauth_google_client_secret.strip())
    if family == "microsoft":
        return bool(settings.oauth_microsoft_client_id.strip() and settings.oauth_microsoft_client_secret.strip())
    if family == "github":
        return bool(settings.oauth_github_client_id.strip() and settings.oauth_github_client_secret.strip())
    if family == "notion":
        return bool(settings.oauth_notion_client_id.strip() and settings.oauth_notion_client_secret.strip())
    if family == "stripe":
        return bool(settings.oauth_stripe_client_id.strip() and settings.oauth_stripe_client_secret.strip())
    if family == "meta":
        return bool(settings.oauth_meta_client_id.strip() and settings.oauth_meta_client_secret.strip())
    if family == "x":
        return bool(settings.oauth_x_client_id.strip() and settings.oauth_x_client_secret.strip())
    if family == "tiktok":
        return bool(settings.oauth_tiktok_client_key.strip() and settings.oauth_tiktok_client_secret.strip())
    return False


def oauth_catalog_snapshot(settings: Settings) -> dict[str, Any]:
    """JSON-safe snapshot for ``GET /connectors/catalog`` and ``GET /oauth/providers``."""

    items: list[dict[str, Any]] = []
    for spec in OAUTH_SURFACES.values():
        fam = spec.vendor_family
        items.append(
            {
                "provider_key": spec.provider_key,
                "label": spec.label,
                "template_id": spec.template_id,
                "vendor_family": fam,
                "configured": _family_configured(settings, fam),
                "uses_pkce": spec.uses_pkce,
            },
        )
    return {
        "redirect_uri": settings.oauth_redirect_uri,
        "providers": items,
    }


def client_credentials_for_family(settings: Settings, family: VendorFamily) -> tuple[str, str]:
    """Resolve OAuth client id + secret for the vendor family."""

    if family == "google":
        return settings.oauth_google_client_id.strip(), settings.oauth_google_client_secret.strip()
    if family == "microsoft":
        return settings.oauth_microsoft_client_id.strip(), settings.oauth_microsoft_client_secret.strip()
    if family == "github":
        return settings.oauth_github_client_id.strip(), settings.oauth_github_client_secret.strip()
    if family == "notion":
        return settings.oauth_notion_client_id.strip(), settings.oauth_notion_client_secret.strip()
    if family == "stripe":
        return settings.oauth_stripe_client_id.strip(), settings.oauth_stripe_client_secret.strip()
    if family == "meta":
        return settings.oauth_meta_client_id.strip(), settings.oauth_meta_client_secret.strip()
    if family == "x":
        return settings.oauth_x_client_id.strip(), settings.oauth_x_client_secret.strip()
    if family == "tiktok":
        return settings.oauth_tiktok_client_key.strip(), settings.oauth_tiktok_client_secret.strip()
    msg = f"unsupported oauth vendor family: {family}"
    raise ValueError(msg)


__all__ = [
    "OAUTH_SURFACES",
    "OAuthSurfaceSpec",
    "VendorFamily",
    "client_credentials_for_family",
    "oauth_catalog_snapshot",
]
