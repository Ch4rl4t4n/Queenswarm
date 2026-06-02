/** Session guardrails from ``GET/PATCH /auth/session-policy``. */

export type SessionPolicySource = "deployment" | "tenant";

export interface SessionPolicySnapshot {
  access_token_expire_minutes: number;
  refresh_token_expire_days: number;
  dashboard_2fa_session_max_hours: number;
  rate_limit_enabled: boolean;
  rate_limit_requests: number;
  rate_limit_window_sec: number;
  oauth_pkce_enabled: boolean;
  oauth_state_ttl_sec: number;
  production_security_mode: boolean;
  two_fa_enabled: boolean;
  editable: boolean;
  access_token_source: SessionPolicySource;
  access_token_minutes_custom: number | null;
  access_token_minutes_deployment: number;
  refresh_token_source: SessionPolicySource;
  refresh_token_days_custom: number | null;
  refresh_token_days_deployment: number;
  dashboard_2fa_session_source: SessionPolicySource;
  dashboard_2fa_session_max_hours_custom: number | null;
  dashboard_2fa_session_max_hours_deployment: number;
  rate_limit_source: SessionPolicySource;
  rate_limit_enabled_custom: boolean | null;
  rate_limit_requests_custom: number | null;
  rate_limit_window_sec_custom: number | null;
  rate_limit_enabled_deployment: boolean;
  rate_limit_requests_deployment: number;
  rate_limit_window_sec_deployment: number;
  oauth_pkce_source: SessionPolicySource;
  oauth_pkce_enabled_custom: boolean | null;
  oauth_state_ttl_sec_custom: number | null;
  oauth_pkce_enabled_deployment: boolean;
  oauth_state_ttl_sec_deployment: number;
}

export interface SessionPolicyPatch {
  access_token_source?: SessionPolicySource;
  access_token_minutes?: number;
  refresh_token_source?: SessionPolicySource;
  refresh_token_days?: number;
  rate_limit_source?: SessionPolicySource;
  rate_limit_enabled?: boolean;
  rate_limit_requests?: number;
  rate_limit_window_sec?: number;
  oauth_pkce_source?: SessionPolicySource;
  oauth_pkce_enabled?: boolean;
  oauth_state_ttl_sec?: number;
  dashboard_2fa_session_source?: SessionPolicySource;
  dashboard_2fa_session_max_hours?: number;
}

export interface SessionPolicyDraft {
  access_token_source: SessionPolicySource;
  access_token_minutes: number;
  refresh_token_source: SessionPolicySource;
  refresh_token_days: number;
  dashboard_2fa_session_source: SessionPolicySource;
  dashboard_2fa_session_max_hours: number;
  rate_limit_source: SessionPolicySource;
  rate_limit_enabled: boolean;
  rate_limit_requests: number;
  rate_limit_window_sec: number;
  oauth_pkce_source: SessionPolicySource;
  oauth_pkce_enabled: boolean;
  oauth_state_ttl_sec: number;
}

export function draftFromSessionPolicy(policy: SessionPolicySnapshot): SessionPolicyDraft {
  return {
    access_token_source: policy.access_token_source,
    access_token_minutes: policy.access_token_minutes_custom ?? policy.access_token_expire_minutes,
    refresh_token_source: policy.refresh_token_source,
    refresh_token_days: policy.refresh_token_days_custom ?? policy.refresh_token_expire_days,
    dashboard_2fa_session_source: policy.dashboard_2fa_session_source,
    dashboard_2fa_session_max_hours:
      policy.dashboard_2fa_session_max_hours_custom ?? policy.dashboard_2fa_session_max_hours,
    rate_limit_source: policy.rate_limit_source,
    rate_limit_enabled: policy.rate_limit_enabled_custom ?? policy.rate_limit_enabled,
    rate_limit_requests: policy.rate_limit_requests_custom ?? policy.rate_limit_requests,
    rate_limit_window_sec: policy.rate_limit_window_sec_custom ?? policy.rate_limit_window_sec,
    oauth_pkce_source: policy.oauth_pkce_source,
    oauth_pkce_enabled: policy.oauth_pkce_enabled_custom ?? policy.oauth_pkce_enabled,
    oauth_state_ttl_sec: policy.oauth_state_ttl_sec_custom ?? policy.oauth_state_ttl_sec,
  };
}

export function patchFromDraft(draft: SessionPolicyDraft): SessionPolicyPatch {
  return {
    access_token_source: draft.access_token_source,
    access_token_minutes: draft.access_token_source === "tenant" ? draft.access_token_minutes : undefined,
    refresh_token_source: draft.refresh_token_source,
    refresh_token_days: draft.refresh_token_source === "tenant" ? draft.refresh_token_days : undefined,
    rate_limit_source: draft.rate_limit_source,
    rate_limit_enabled: draft.rate_limit_source === "tenant" ? draft.rate_limit_enabled : undefined,
    rate_limit_requests: draft.rate_limit_source === "tenant" ? draft.rate_limit_requests : undefined,
    rate_limit_window_sec: draft.rate_limit_source === "tenant" ? draft.rate_limit_window_sec : undefined,
    oauth_pkce_source: draft.oauth_pkce_source,
    oauth_pkce_enabled: draft.oauth_pkce_source === "tenant" ? draft.oauth_pkce_enabled : undefined,
    oauth_state_ttl_sec: draft.oauth_pkce_source === "tenant" ? draft.oauth_state_ttl_sec : undefined,
    dashboard_2fa_session_source: draft.dashboard_2fa_session_source,
    dashboard_2fa_session_max_hours:
      draft.dashboard_2fa_session_source === "tenant" ? draft.dashboard_2fa_session_max_hours : undefined,
  };
}
