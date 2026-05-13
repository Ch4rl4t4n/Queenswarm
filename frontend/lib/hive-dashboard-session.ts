/**
 * `/api/v1/auth/*` and related dashboard-session payloads mirrored from FastAPI routers.
 */

export interface DeliveryChannelsState {
  email?: { enabled?: boolean; address?: string | null };
  sms?: { enabled?: boolean; phone_e164?: string | null };
  discord?: { enabled?: boolean; webhook_url?: string | null };
  telegram?: { enabled?: boolean; bot_token?: string | null; chat_id?: string | null };
}

/** Shape inside ``dashboard_users.notification_prefs``. */
export interface DeliveryChannelsPrefs extends Record<string, unknown> {
  delivery_channels?: DeliveryChannelsState;
}

export interface DashboardOperatorMe {
  email: string;
  display_name: string | null;
  timezone: string | null;
  notification_prefs: Record<string, unknown>;
  scopes: string[];
  is_admin: boolean;
  totp_required: boolean;
  totp_has_secret: boolean;
  totp_verified_at: string | null;
  /** Present on API ≥ backup-codes release; treat as 0 if missing. */
  totp_backup_codes_remaining?: number;
  totp_backup_last_used_at?: string | null;
  audit_log_enabled?: boolean;
  /** Computed server-side — secret persisted and verifier completed successfully. */
  totp_enabled?: boolean;
}

export interface LlmProvidersStatus {
  grok_configured: boolean;
  anthropic_configured: boolean;
  openai_configured: boolean;
  grok_from_vault: boolean;
  anthropic_from_vault: boolean;
  openai_from_vault: boolean;
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
  /** Machine slug for integrations (stored server-side); legacy keys may omit. */
  source_name: string | null;
  label: string | null;
  masked_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyCreated extends ApiKeyListItem {
  plaintext: string;
}

export interface TotpProvisionResponse {
  secret_base32: string;
  otpauth_uri: string;
}

export interface TotpConfirmResponse {
  verified: boolean;
  backup_codes: string[] | null;
}

export interface BackupCodesRegenerateResponse {
  codes: string[];
}
