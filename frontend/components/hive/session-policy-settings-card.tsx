"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Toggle } from "@/components/ui/toggle";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hivePatchJson } from "@/lib/api";
import type { SessionPolicyDraft, SessionPolicySnapshot, SessionPolicySource } from "@/lib/session-policy-types";
import { draftFromSessionPolicy, patchFromDraft } from "@/lib/session-policy-types";
import {
  formatAccessTtl,
  formatOAuthStateTtl,
  formatRateLimit,
  formatRefreshTtl,
  nearestSelectValue,
} from "@/lib/session-policy-utils";

const SOURCE_OPTIONS = [
  { value: "deployment", label: "Deployment default" },
  { value: "tenant", label: "Custom for this tenant" },
] as const;

const ACCESS_MINUTES_OPTIONS = [5, 15, 30, 60, 120, 240] as const;
const REFRESH_DAYS_OPTIONS = [1, 7, 14, 30, 90, 180] as const;
const RATE_REQUESTS_OPTIONS = [100, 600, 1200, 2400, 6000] as const;
const RATE_WINDOW_OPTIONS = [60, 120, 300] as const;
const OAUTH_TTL_OPTIONS = [300, 600, 900, 1800, 3600] as const;

interface SessionPolicySettingsCardProps {
  readonly policy: SessionPolicySnapshot | null;
  readonly onSaved: (policy: SessionPolicySnapshot) => void;
}

function sourceLabel(source: SessionPolicySource): string {
  return source === "tenant" ? "tenant custom" : "deployment";
}

export function SessionPolicySettingsCard({ policy, onSaved }: SessionPolicySettingsCardProps): JSX.Element {
  const [draft, setDraft] = useState<SessionPolicyDraft | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (policy) {
      setDraft(draftFromSessionPolicy(policy));
    }
  }, [policy]);

  const effectivePreview = useMemo(() => {
    if (!policy || !draft) {
      return null;
    }
    const accessMinutes =
      draft.access_token_source === "tenant" ? draft.access_token_minutes : policy.access_token_minutes_deployment;
    const refreshDays =
      draft.refresh_token_source === "tenant" ? draft.refresh_token_days : policy.refresh_token_days_deployment;
    const rateEnabled =
      draft.rate_limit_source === "tenant" ? draft.rate_limit_enabled : policy.rate_limit_enabled_deployment;
    const rateRequests =
      draft.rate_limit_source === "tenant" ? draft.rate_limit_requests : policy.rate_limit_requests_deployment;
    const rateWindow =
      draft.rate_limit_source === "tenant" ? draft.rate_limit_window_sec : policy.rate_limit_window_sec_deployment;
    const oauthEnabled =
      draft.oauth_pkce_source === "tenant" ? draft.oauth_pkce_enabled : policy.oauth_pkce_enabled_deployment;
    const oauthTtl =
      draft.oauth_pkce_source === "tenant" ? draft.oauth_state_ttl_sec : policy.oauth_state_ttl_sec_deployment;
    return {
      accessMinutes,
      refreshDays,
      rateEnabled,
      rateRequests,
      rateWindow,
      oauthEnabled,
      oauthTtl,
    };
  }, [draft, policy]);

  async function savePolicy(): Promise<void> {
    if (!draft || !policy?.editable) {
      return;
    }
    setBusy(true);
    try {
      const saved = await hivePatchJson<SessionPolicySnapshot>("auth/session-policy", patchFromDraft(draft));
      onSaved(saved);
      setDraft(draftFromSessionPolicy(saved));
      toast.success("Session policy saved — new logins use updated TTLs.");
    } catch (error) {
      const message = error instanceof HiveApiError ? error.message : "Unable to save session policy.";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <V4Card>
      <V4CardHeader
        as="h3"
        title="Session policy"
        description="JWT, refresh, and rate-limit guardrails — choose deployment defaults or tenant-specific values."
      />
      {!policy || !draft || !effectivePreview ? (
        <p className="text-sm text-(--qs-text-3)">Loading session policy…</p>
      ) : (
        <div className="mt-2 space-y-0">
          <div className="v4-session-policy-row">
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-medium text-(--qs-text)">JWT access token TTL</p>
                <p className="text-sm text-(--qs-text-3)">
                  Effective {formatAccessTtl(effectivePreview.accessMinutes)} · source{" "}
                  <span className="font-mono text-(--qs-text-2)">{sourceLabel(draft.access_token_source)}</span>
                </p>
              </div>
              {policy.editable ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  <label className="grid gap-1.5">
                    <span className="v4-field-label">When to apply</span>
                    <QsSelect
                      aria-label="JWT access token source"
                      value={draft.access_token_source}
                      options={[...SOURCE_OPTIONS]}
                      onValueChange={(value) =>
                      setDraft((current) =>
                        current
                          ? {
                              ...current,
                              access_token_source: value as SessionPolicySource,
                              access_token_minutes: nearestSelectValue(
                                current.access_token_minutes,
                                ACCESS_MINUTES_OPTIONS,
                              ),
                            }
                          : current,
                      )
                    }
                  />
                  </label>
                  {draft.access_token_source === "tenant" ? (
                    <label className="grid gap-1.5">
                      <span className="v4-field-label">Custom TTL</span>
                      <QsSelect
                        aria-label="JWT access token custom TTL"
                        value={String(draft.access_token_minutes)}
                        options={ACCESS_MINUTES_OPTIONS.map((minutes) => ({
                          value: String(minutes),
                          label: formatAccessTtl(minutes),
                        }))}
                        onValueChange={(value) =>
                          setDraft((current) =>
                            current ? { ...current, access_token_minutes: Number(value) } : current,
                          )
                        }
                      />
                    </label>
                  ) : null}
                </div>
              ) : null}
            </div>
            <V4Badge tone="info" className="shrink-0 tabular-nums">
              {formatAccessTtl(effectivePreview.accessMinutes)}
            </V4Badge>
          </div>

          <div className="v4-session-policy-row">
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-medium text-(--qs-text)">Refresh token TTL</p>
                <p className="text-sm text-(--qs-text-3)">
                  Effective {formatRefreshTtl(effectivePreview.refreshDays)} · source{" "}
                  <span className="font-mono text-(--qs-text-2)">{sourceLabel(draft.refresh_token_source)}</span>
                </p>
              </div>
              {policy.editable ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  <label className="grid gap-1.5">
                    <span className="v4-field-label">When to apply</span>
                    <QsSelect
                      aria-label="Refresh token source"
                      value={draft.refresh_token_source}
                      options={[...SOURCE_OPTIONS]}
                      onValueChange={(value) =>
                        setDraft((current) =>
                          current
                            ? {
                                ...current,
                                refresh_token_source: value as SessionPolicySource,
                                refresh_token_days: nearestSelectValue(
                                  current.refresh_token_days,
                                  REFRESH_DAYS_OPTIONS,
                                ),
                              }
                            : current,
                        )
                      }
                    />
                  </label>
                  {draft.refresh_token_source === "tenant" ? (
                    <label className="grid gap-1.5">
                      <span className="v4-field-label">Custom TTL</span>
                      <QsSelect
                        aria-label="Refresh token custom TTL"
                        value={String(draft.refresh_token_days)}
                        options={REFRESH_DAYS_OPTIONS.map((days) => ({
                          value: String(days),
                          label: formatRefreshTtl(days),
                        }))}
                        onValueChange={(value) =>
                          setDraft((current) =>
                            current ? { ...current, refresh_token_days: Number(value) } : current,
                          )
                        }
                      />
                    </label>
                  ) : null}
                </div>
              ) : null}
            </div>
            <V4Badge tone="info" className="shrink-0 tabular-nums">
              {formatRefreshTtl(effectivePreview.refreshDays)}
            </V4Badge>
          </div>

          <div className="v4-session-policy-row">
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-medium text-(--qs-text)">Rate limit (per user)</p>
                <p className="text-sm text-(--qs-text-3)">
                  {effectivePreview.rateEnabled
                    ? formatRateLimit({
                        rate_limit_requests: effectivePreview.rateRequests,
                        rate_limit_window_sec: effectivePreview.rateWindow,
                      })
                    : "Disabled for this tenant"}
                  {" · "}
                  source <span className="font-mono text-(--qs-text-2)">{sourceLabel(draft.rate_limit_source)}</span>
                </p>
              </div>
              {policy.editable ? (
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <label className="grid gap-1.5">
                    <span className="v4-field-label">When to apply</span>
                    <QsSelect
                      aria-label="Rate limit source"
                      value={draft.rate_limit_source}
                      options={[...SOURCE_OPTIONS]}
                      onValueChange={(value) =>
                        setDraft((current) =>
                          current ? { ...current, rate_limit_source: value as SessionPolicySource } : current,
                        )
                      }
                    />
                  </label>
                  {draft.rate_limit_source === "tenant" ? (
                    <>
                      <label className="flex items-center justify-between gap-3 rounded-xl border border-(--qs-border) bg-black/25 px-3 py-2 text-xs text-(--qs-text-2)">
                        <span>Enforce limit</span>
                        <Toggle
                          checked={draft.rate_limit_enabled}
                          onChange={(next) =>
                            setDraft((current) => (current ? { ...current, rate_limit_enabled: next } : current))
                          }
                        />
                      </label>
                      <label className="grid gap-1.5">
                        <span className="v4-field-label">Requests</span>
                        <QsSelect
                          aria-label="Rate limit requests"
                          value={String(draft.rate_limit_requests)}
                          options={RATE_REQUESTS_OPTIONS.map((count) => ({
                            value: String(count),
                            label: `${count} req`,
                          }))}
                          onValueChange={(value) =>
                            setDraft((current) =>
                              current ? { ...current, rate_limit_requests: Number(value) } : current,
                            )
                          }
                        />
                      </label>
                      <label className="grid gap-1.5">
                        <span className="v4-field-label">Window (sec)</span>
                        <QsSelect
                          aria-label="Rate limit window"
                          value={String(Math.round(draft.rate_limit_window_sec))}
                          options={RATE_WINDOW_OPTIONS.map((seconds) => ({
                            value: String(seconds),
                            label: `${seconds}s`,
                          }))}
                          onValueChange={(value) =>
                            setDraft((current) =>
                              current ? { ...current, rate_limit_window_sec: Number(value) } : current,
                            )
                          }
                        />
                      </label>
                    </>
                  ) : null}
                </div>
              ) : null}
            </div>
            <V4Badge tone={effectivePreview.rateEnabled ? "ok" : "warn"}>
              {effectivePreview.rateEnabled ? "enforced" : "off"}
            </V4Badge>
          </div>

          <div className="v4-session-policy-row v4-session-policy-row--last">
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-medium text-(--qs-text)">OAuth consent (PKCE)</p>
                <p className="text-sm text-(--qs-text-3)">
                  {effectivePreview.oauthEnabled ? formatOAuthStateTtl(effectivePreview.oauthTtl) : "Disabled"}
                  {" · "}
                  source <span className="font-mono text-(--qs-text-2)">{sourceLabel(draft.oauth_pkce_source)}</span>
                </p>
              </div>
              {policy.editable ? (
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  <label className="grid gap-1.5">
                    <span className="v4-field-label">When to apply</span>
                    <QsSelect
                      aria-label="OAuth PKCE source"
                      value={draft.oauth_pkce_source}
                      options={[...SOURCE_OPTIONS]}
                      onValueChange={(value) =>
                        setDraft((current) =>
                          current ? { ...current, oauth_pkce_source: value as SessionPolicySource } : current,
                        )
                      }
                    />
                  </label>
                  {draft.oauth_pkce_source === "tenant" ? (
                    <>
                      <label className="flex items-center justify-between gap-3 rounded-xl border border-(--qs-border) bg-black/25 px-3 py-2 text-xs text-(--qs-text-2)">
                        <span>PKCE enabled</span>
                        <Toggle
                          checked={draft.oauth_pkce_enabled}
                          onChange={(next) =>
                            setDraft((current) => (current ? { ...current, oauth_pkce_enabled: next } : current))
                          }
                        />
                      </label>
                      <label className="grid gap-1.5">
                        <span className="v4-field-label">Redis state TTL</span>
                        <QsSelect
                          aria-label="OAuth state TTL"
                          value={String(draft.oauth_state_ttl_sec)}
                          options={OAUTH_TTL_OPTIONS.map((seconds) => ({
                            value: String(seconds),
                            label: formatOAuthStateTtl(seconds),
                          }))}
                          onValueChange={(value) =>
                            setDraft((current) =>
                              current ? { ...current, oauth_state_ttl_sec: Number(value) } : current,
                            )
                          }
                        />
                      </label>
                    </>
                  ) : null}
                </div>
              ) : null}
            </div>
            <V4Badge tone={effectivePreview.oauthEnabled ? "ok" : "warn"}>
              {effectivePreview.oauthEnabled ? "enabled" : "disabled"}
            </V4Badge>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-(--qs-text-3)">
          {policy?.production_security_mode
            ? "Production security mode is active — deployment defaults stay locked; tenant overrides apply when set to Custom."
            : "Choose Deployment default or Custom per row. JWT/refresh changes apply on next login."}
        </p>
        {policy?.editable ? (
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-2"
            disabled={busy || !draft}
            onClick={() => void savePolicy()}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            Save session policy
          </button>
        ) : (
          <p className="text-xs text-(--qs-text-3)">Owner or admin role required to edit.</p>
        )}
      </div>
    </V4Card>
  );
}
