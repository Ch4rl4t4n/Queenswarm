/** Read-only session guardrails from ``GET /auth/session-policy``. */

export interface SessionPolicySnapshot {
  access_token_expire_minutes: number;
  refresh_token_expire_days: number;
  rate_limit_enabled: boolean;
  rate_limit_requests: number;
  rate_limit_window_sec: number;
  oauth_state_ttl_sec: number;
  production_security_mode: boolean;
  two_fa_enabled: boolean;
  editable: boolean;
}
