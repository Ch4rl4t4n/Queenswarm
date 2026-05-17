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
    id: "stripe",
    phase3TemplateId: "stripe_billing",
    slug: "stripe_billing",
    label: "Stripe Billing",
    kind: "api_key",
    tokenEndpoint: null,
    docsUrl: "https://stripe.com/docs/keys",
    scopesHint: "Restricted secret key — seal as API key; rotate in Stripe Dashboard.",
    probeSuggestion: "https://api.stripe.com/v1/balance",
  },
] as const;

export function presetById(id: string): VaultVendorPreset | undefined {
  return VAULT_VENDOR_PRESETS.find((p) => p.id === id);
}
