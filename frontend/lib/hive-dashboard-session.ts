/**
 * `/api/v1/auth/*` and related dashboard-session payloads mirrored from FastAPI routers.
 */

export interface DashboardOperatorMe {
  email: string;
  display_name: string | null;
  timezone: string | null;
  notification_prefs: Record<string, boolean>;
  scopes: string[];
  is_admin: boolean;
  totp_required: boolean;
  totp_has_secret: boolean;
  totp_verified_at: string | null;
}

export interface LlmProvidersStatus {
  grok_configured: boolean;
  anthropic_configured: boolean;
  openai_configured: boolean;
}

export interface HiveCostSummary {
  window_started_at: string;
  spent_usd_rolling_30d: number;
  monthly_budget_cap_usd: number;
  weekly_budget_usd: number;
  daily_budget_usd: number;
  cost_warning_threshold: number;
}

export interface ApiKeyListItem {
  id: string;
  label: string | null;
  masked_prefix: string;
  created_at: string;
  revoked_at: string | null;
}

export interface ApiKeyCreated extends ApiKeyListItem {
  plaintext: string;
}

export interface TotpProvisionResponse {
  secret_base32: string;
  otpauth_uri: string;
}
