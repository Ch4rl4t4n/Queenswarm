/**
 * Phase 3.6 — Vault wizard presets aligned with Phase 3 MCP templates (`phase3/catalog.py` suggested_slug values).
 *
 * Queenswarm uses operator-hosted OAuth (vault seal + refresh + ping) — there is no in-app browser OAuth consent
 * redirect today; these presets accelerate correct slug/token-endpoint pairing and documented flows.
 */

export type VaultPresetKind = "oauth2" | "api_key";

export interface VaultVendorPreset {
  /** Stable id for analytics / tests */
  readonly id: string;
  readonly phase3TemplateId: string;
  readonly slug: string;
  readonly label: string;
  readonly kind: VaultPresetKind;
  /** OAuth token URL — null for API-key vendors */
  readonly tokenEndpoint: string | null;
  readonly docsUrl: string;
  readonly scopesHint: string;
  readonly probeSuggestion: string | null;
}

export const VAULT_VENDOR_PRESETS: readonly VaultVendorPreset[] = [
  {
    id: "gmail",
    phase3TemplateId: "gmail_google_workspace",
    slug: "gmail_workspace",
    label: "Gmail (Google Workspace)",
    kind: "oauth2",
    tokenEndpoint: "https://oauth2.googleapis.com/token",
    docsUrl: "https://developers.google.com/gmail/api/quickstart/js",
    scopesHint:
      "Gmail API readonly/send scopes via Google Cloud OAuth client (installed or web). Paste refresh + access tokens after consent.",
    probeSuggestion: "https://gmail.googleapis.com/gmail/v1/users/me/profile",
  },
  {
    id: "outlook",
    phase3TemplateId: "outlook_microsoft365",
    slug: "outlook_graph",
    label: "Outlook / Microsoft 365",
    kind: "oauth2",
    tokenEndpoint: "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    docsUrl: "https://learn.microsoft.com/en-us/graph/auth-v2-user",
    scopesHint: "Azure AD app registration — delegated Mail / Calendars; use refresh token flow.",
    probeSuggestion: "https://graph.microsoft.com/v1.0/me",
  },
  {
    id: "google_calendar",
    phase3TemplateId: "google_calendar",
    slug: "google_calendar",
    label: "Google Calendar",
    kind: "oauth2",
    tokenEndpoint: "https://oauth2.googleapis.com/token",
    docsUrl: "https://developers.google.com/calendar/api/guides/auth",
    scopesHint: "Same Google OAuth client as Gmail or dedicated — calendar.readonly / calendar.events.",
    probeSuggestion: "https://www.googleapis.com/calendar/v3/users/me/calendarList",
  },
  {
    id: "github",
    phase3TemplateId: "github_rest",
    slug: "github_rest",
    label: "GitHub REST",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token",
    scopesHint: "Fine-grained or classic PAT — seal as API key; ping uses Authorization bearer.",
    probeSuggestion: "https://api.github.com/user",
  },
  {
    id: "gitlab",
    phase3TemplateId: "gitlab_rest",
    slug: "gitlab_rest",
    label: "GitLab REST",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html",
    scopesHint: "Personal access token with API scope for your instance.",
    probeSuggestion: null,
  },
  {
    id: "slack",
    phase3TemplateId: "slack_workspace",
    slug: "slack_workspace",
    label: "Slack workspace",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://api.slack.com/authentication/token-types",
    scopesHint: "Bot user OAuth token (`xoxb-…`) — seal as API key unless using OAuth refresh separately.",
    probeSuggestion: "https://slack.com/api/auth.test",
  },
  {
    id: "telegram",
    phase3TemplateId: "telegram_bot",
    slug: "telegram_bot",
    label: "Telegram Bot API",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://core.telegram.org/bots/tutorial",
    scopesHint: "Bot token from BotFather — seal as API key.",
    probeSuggestion: null,
  },
  {
    id: "discord",
    phase3TemplateId: "discord_guild",
    slug: "discord_guild",
    label: "Discord Bot",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://discord.com/developers/docs/topics/oauth2",
    scopesHint: "Bot token from Discord Developer Portal — seal as API key.",
    probeSuggestion: null,
  },
  {
    id: "notion",
    phase3TemplateId: "notion_workspace",
    slug: "notion_workspace",
    label: "Notion",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://developers.notion.com/docs/create-a-notion-integration",
    scopesHint: "Internal integration secret — seal as API key (Notion-Version header handled in manifests).",
    probeSuggestion: "https://api.notion.com/v1/users/me",
  },
  {
    id: "instagram_graph",
    phase3TemplateId: "instagram_graph_api",
    slug: "instagram_graph",
    label: "Instagram · Meta Graph",
    kind: "oauth2",
    tokenEndpoint: "https://graph.facebook.com/v21.0/oauth/access_token",
    docsUrl: "https://developers.facebook.com/docs/instagram-api/guides/content-publishing",
    scopesHint:
      "Meta Business app — instagram_basic, instagram_content_publish, pages_show_list. Prefer hosted OAuth Connect in Connector Hub.",
    probeSuggestion: null,
  },
  {
    id: "facebook_graph",
    phase3TemplateId: "facebook_graph_api",
    slug: "facebook_graph",
    label: "Facebook · Meta Graph Pages",
    kind: "oauth2",
    tokenEndpoint: "https://graph.facebook.com/v21.0/oauth/access_token",
    docsUrl: "https://developers.facebook.com/docs/pages-api/posts",
    scopesHint: "Same Meta app as Instagram — pages_manage_posts for Page feed posts.",
    probeSuggestion: null,
  },
  {
    id: "twitter_api_v2",
    phase3TemplateId: "twitter_api_v2",
    slug: "twitter_api_v2",
    label: "X (Twitter) · API v2",
    kind: "oauth2",
    tokenEndpoint: "https://api.twitter.com/2/oauth2/token",
    docsUrl: "https://developer.x.com/en/docs/authentication/oauth-2-0/user-access-token",
    scopesHint: "OAuth 2.0 user context — tweet.read, tweet.write, users.read, offline.access. PKCE required.",
    probeSuggestion: "https://api.twitter.com/2/users/me",
  },
  {
    id: "tiktok_content",
    phase3TemplateId: "tiktok_content_posting",
    slug: "tiktok_content",
    label: "TikTok · Content Posting API",
    kind: "oauth2",
    tokenEndpoint: "https://open.tiktokapis.com/v2/oauth/token/",
    docsUrl: "https://developers.tiktok.com/doc/content-posting-api-get-started",
    scopesHint: "user.info.basic, video.publish — PKCE required; app review before live.",
    probeSuggestion: null,
  },
  {
    id: "polymarket_gamma",
    phase3TemplateId: "polymarket_gamma_api",
    slug: "polymarket_gamma",
    label: "Polymarket · Gamma (markets)",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://docs.polymarket.com/quickstart",
    scopesHint: "No credentials — public market metadata for bot discovery.",
    probeSuggestion: "https://gamma-api.polymarket.com/markets?limit=1",
  },
  {
    id: "polymarket_clob",
    phase3TemplateId: "polymarket_clob_api",
    slug: "polymarket_clob",
    label: "Polymarket · CLOB (trading)",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://docs.polymarket.com/api-reference/authentication",
    scopesHint:
      "Vault fields: polymarket_api_key, polymarket_api_secret, polymarket_api_passphrase, polymarket_wallet_address (L2 creds from wallet).",
    probeSuggestion: null,
  },
] as const;

export function presetById(id: string): VaultVendorPreset | undefined {
  return VAULT_VENDOR_PRESETS.find((p) => p.id === id);
}
