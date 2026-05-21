"use client";

import { ClipboardListIcon, DownloadIcon, Loader2Icon, MailIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { V4Badge, V4Card } from "@/components/ui/v4";
import { AuditRollupTrendChart } from "@/components/hive/audit-rollup-trend-chart";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import {
  auditDigestHealthLabel,
  auditDigestHealthTone,
  formatDigestSentAt,
  rollupDigestNeedsBulkSend,
  tenantDigestNeedsManualSend,
  type AuditDigestHealth,
  type AuditDigestHealthSummary,
} from "@/lib/audit-rollup-utils";

interface AuditDigestRollupTenant {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  platform_mode: string;
  action_count: number;
  session_count: number;
  action_counts: Record<string, number>;
  digest_enabled: boolean;
  digest_health: AuditDigestHealth;
  last_digest_sent_at: string | null;
}

interface AuditDigestRollup {
  window_hours: number;
  generated_at: string;
  tenants_active: number;
  tenants_total: number;
  total_actions: number;
  global_action_counts: Record<string, number>;
  daily_trend: Array<{ date: string; action_count: number; tenants_active: number }>;
  digest_health_summary?: AuditDigestHealthSummary;
  tenants: AuditDigestRollupTenant[];
  cached?: boolean;
}

interface CommandCenterAuditRollupCardProps {
  enabled: boolean;
}

/** Cross-tenant supervisor operator audit weekly rollup for internal admins. */
export function CommandCenterAuditRollupCard({ enabled }: CommandCenterAuditRollupCardProps) {
  const [rollup, setRollup] = useState<AuditDigestRollup | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState<"csv" | "markdown" | null>(null);
  const [sendBusy, setSendBusy] = useState(false);
  const [bulkDigestBusy, setBulkDigestBusy] = useState(false);
  const [tenantDigestBusyId, setTenantDigestBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    try {
      const body = await hiveGet<AuditDigestRollup>("operator/command-center/audit-digest-rollup?window_hours=168");
      setRollup(body);
      setError(null);
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Audit rollup unavailable.";
      setError(msg);
      setRollup(null);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void load();
  }, [load]);

  async function exportRollup(format: "csv" | "markdown"): Promise<void> {
    setExportBusy(format);
    try {
      const res = await fetch(
        `/api/proxy/operator/command-center/audit-digest-rollup/export?format=${format}&window_hours=168`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        throw new Error("Export failed");
      }
      const blob = await res.blob();
      const stamp = new Date().toISOString().slice(0, 10);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `supervisor-audit-rollup-${stamp}.${format === "csv" ? "csv" : "md"}`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success(`Rollup exported (${format.toUpperCase()}).`);
    } catch (exc) {
      toast.error(exc instanceof Error ? exc.message : "Export failed");
    } finally {
      setExportBusy(null);
    }
  }

  async function sendRollupEmail(): Promise<void> {
    setSendBusy(true);
    try {
      const result = await hivePostJson<{
        sent: boolean;
        reason?: string | null;
        sent_count?: number;
        slack_sent?: boolean;
        digest_stale_count?: number;
        digest_never_sent_count?: number;
        digest_needs_attention?: boolean;
      }>("operator/command-center/audit-digest-rollup/send?window_hours=168", {});
      if (result.sent) {
        const channels = [
          (result.sent_count ?? 0) > 0 ? "email" : null,
          result.slack_sent ? "Slack" : null,
        ]
          .filter(Boolean)
          .join(" + ");
        const alertSuffix =
          result.digest_needs_attention
            ? ` · ${result.digest_stale_count ?? 0} stale / ${result.digest_never_sent_count ?? 0} never sent`
            : "";
        toast.success(`Platform rollup sent via ${channels || "configured channels"}${alertSuffix}.`);
        await load();
      } else {
        toast.message(result.reason ?? "Rollup not sent.");
      }
    } catch (exc) {
      toast.error(exc instanceof HiveApiError ? exc.message : "Send failed");
    } finally {
      setSendBusy(false);
    }
  }

  async function sendAttentionDigests(): Promise<void> {
    setBulkDigestBusy(true);
    try {
      const result = await hivePostJson<{
        sent: boolean;
        reason?: string | null;
        tenants_attempted?: number;
        tenants_sent?: number;
        digest_stale_count?: number;
        digest_never_sent_count?: number;
      }>("operator/command-center/audit-digest-rollup/send-attention-digests?window_hours=168", {});
      if (result.sent) {
        toast.success(
          `Digests sent for ${result.tenants_sent ?? 0}/${result.tenants_attempted ?? 0} alert hives.`,
        );
        await load();
      } else {
        toast.message(result.reason ?? "No alert digests sent.");
      }
    } catch (exc) {
      toast.error(exc instanceof HiveApiError ? exc.message : "Bulk digest send failed");
    } finally {
      setBulkDigestBusy(false);
    }
  }

  async function sendTenantDigest(tenant: AuditDigestRollupTenant): Promise<void> {
    setTenantDigestBusyId(tenant.tenant_id);
    try {
      const result = await hivePostJson<{
        sent: boolean;
        reason?: string | null;
        sent_count?: number;
        action_count?: number;
      }>(
        `operator/command-center/audit-digest-rollup/tenants/${tenant.tenant_id}/send-digest?window_hours=168`,
        {},
      );
      if (result.sent) {
        toast.success(
          `Digest sent for ${tenant.tenant_name} (${result.action_count ?? 0} actions).`,
        );
        await load();
      } else {
        toast.message(result.reason ?? "Digest not sent.");
      }
    } catch (exc) {
      toast.error(exc instanceof HiveApiError ? exc.message : "Tenant digest send failed");
    } finally {
      setTenantDigestBusyId(null);
    }
  }

  if (!enabled) {
    return null;
  }

  return (
    <V4Card className="overflow-hidden p-0">
      <div className="border-b border-(--qs-border) px-4 py-4 md:px-6">
        <div className="v4-section-header-row mb-0">
          <div className="min-w-0 flex-1">
            <h3>Supervisor audit rollup</h3>
            <p className="desc">
              Cross-tenant operator session actions over the last 7 days — digest schedule health per hive.
            </p>
          </div>
          <div className="v4-section-icon" aria-hidden>
            <ClipboardListIcon className="h-5 w-5" />
          </div>
        </div>
        <div className="v4-toolbar-row mt-3">
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5"
            disabled={exportBusy !== null || sendBusy}
            onClick={() => void exportRollup("csv")}
          >
            {exportBusy === "csv" ? (
              <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
            )}
            CSV
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5"
            disabled={exportBusy !== null || sendBusy}
            onClick={() => void exportRollup("markdown")}
          >
            {exportBusy === "markdown" ? (
              <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
            )}
            MD
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5"
            disabled={sendBusy || exportBusy !== null || bulkDigestBusy}
            onClick={() => void sendRollupEmail()}
          >
            {sendBusy ? (
              <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <MailIcon className="h-3.5 w-3.5" aria-hidden />
            )}
            Send rollup
          </button>
          {rollup && rollupDigestNeedsBulkSend(rollup.digest_health_summary) ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5"
              disabled={bulkDigestBusy || sendBusy || exportBusy !== null || tenantDigestBusyId !== null}
              onClick={() => void sendAttentionDigests()}
            >
              {bulkDigestBusy ? (
                <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : (
                <MailIcon className="h-3.5 w-3.5" aria-hidden />
              )}
              Send all alerts
            </button>
          ) : null}
        </div>
      </div>

      {loading && !rollup ? (
        <div className="flex min-h-[120px] items-center justify-center p-6">
          <Loader2Icon className="h-5 w-5 animate-spin text-pollen" aria-hidden />
        </div>
      ) : error && !rollup ? (
        <p className="p-4 text-sm text-(--qs-red) md:px-6">{error}</p>
      ) : rollup ? (
        <>
          <div className="border-b border-(--qs-border)/70 px-4 py-3 md:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <V4Badge tone="info">{rollup.total_actions} actions</V4Badge>
              <V4Badge tone="ok">{rollup.tenants_active} active hives</V4Badge>
              <V4Badge tone="info">{rollup.tenants_total} tenants total</V4Badge>
              {rollup.cached ? <span className="text-xs text-(--qs-text-3)">cached snapshot</span> : null}
              {(rollup.digest_health_summary?.stale ?? 0) > 0 ? (
                <V4Badge tone="err">{rollup.digest_health_summary?.stale} stale digests</V4Badge>
              ) : null}
              {(rollup.digest_health_summary?.never_sent ?? 0) > 0 ? (
                <V4Badge tone="warn">{rollup.digest_health_summary?.never_sent} never sent</V4Badge>
              ) : null}
            </div>
            <p className="mt-2 text-left text-xs text-(--qs-text-3)">Window: {rollup.window_hours}h</p>
          </div>

          {Object.keys(rollup.global_action_counts).length > 0 ? (
            <div className="flex flex-wrap gap-2 px-4 py-3 md:px-6">
              {Object.entries(rollup.global_action_counts).map(([action, count]) => (
                <V4Badge key={action} tone="info">
                  {action}: {count}
                </V4Badge>
              ))}
            </div>
          ) : null}

          {rollup.daily_trend.length > 0 ? (
            <div className="px-4 py-3 md:px-6">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-cyan">7-day operator trend</p>
              <AuditRollupTrendChart data={rollup.daily_trend} />
            </div>
          ) : null}

          {rollup.tenants.length === 0 ? (
            <p className="px-4 pb-4 text-sm text-(--qs-text-3) md:px-6">
              No supervisor operator actions in this window across active tenants.
            </p>
          ) : (
            <div className="overflow-x-auto hive-scrollbar">
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-(--qs-border) bg-black/25 text-left text-[10px] uppercase tracking-wide text-(--qs-text-3)">
                    <th className="px-4 py-2 md:px-6">Tenant</th>
                    <th className="px-3 py-2">Mode</th>
                    <th className="px-3 py-2">Actions</th>
                    <th className="px-3 py-2">Sessions</th>
                    <th className="px-3 py-2">Digest</th>
                    <th className="px-3 py-2">Send</th>
                    <th className="px-4 py-2 md:px-6">Top actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rollup.tenants.map((tenant) => {
                    const topActions = Object.entries(tenant.action_counts)
                      .slice(0, 3)
                      .map(([action, count]) => `${action} (${count})`)
                      .join(" · ");
                    const digestHealth =
                      tenant.digest_health ??
                      (tenant.digest_enabled ? "healthy" : "disabled");
                    const showTenantSend = tenantDigestNeedsManualSend(digestHealth);
                    const tenantSendBusy = tenantDigestBusyId === tenant.tenant_id;
                    return (
                      <tr key={tenant.tenant_id} className="border-b border-(--qs-border)/60">
                        <td className="px-4 py-2.5 md:px-6">
                          <p className="font-medium text-(--qs-text)">{tenant.tenant_name}</p>
                          <p className="font-mono text-[10px] text-(--qs-text-3)">{tenant.tenant_slug}</p>
                        </td>
                        <td className="px-3 py-2.5 capitalize text-(--qs-text-2)">{tenant.platform_mode}</td>
                        <td className="px-3 py-2.5 font-mono text-cyan">{tenant.action_count}</td>
                        <td className="px-3 py-2.5 font-mono text-(--qs-text-2)">{tenant.session_count}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-col gap-1">
                            <V4Badge tone={auditDigestHealthTone(digestHealth)}>
                              {auditDigestHealthLabel(digestHealth)}
                            </V4Badge>
                            {formatDigestSentAt(tenant.last_digest_sent_at) ? (
                              <span className="text-[10px] text-(--qs-text-3)">
                                Last: {formatDigestSentAt(tenant.last_digest_sent_at)}
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          {showTenantSend ? (
                            <button
                              type="button"
                              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
                              disabled={tenantSendBusy || sendBusy || exportBusy !== null}
                              onClick={() => void sendTenantDigest(tenant)}
                            >
                              {tenantSendBusy ? (
                                <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
                              ) : (
                                <MailIcon className="h-3.5 w-3.5" aria-hidden />
                              )}
                              Send digest
                            </button>
                          ) : (
                            <span className="text-[10px] text-(--qs-text-3)">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-xs text-(--qs-text-3) md:px-6">{topActions || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="border-t border-(--qs-border)/70 px-4 py-3 text-xs text-(--qs-text-3) md:px-6">
            Per-tenant digest schedule and manual send:{" "}
            <Link href="/settings/audit" className="text-cyan hover:underline">
              Settings → Audit log
            </Link>
            {(rollup.digest_health_summary?.stale ?? 0) > 0 ||
            (rollup.digest_health_summary?.never_sent ?? 0) > 0 ? (
              <span className="text-(--qs-text-3)">
                {" "}
                · Review stale or never-sent hives in the table above.
              </span>
            ) : null}
          </div>
        </>
      ) : null}
    </V4Card>
  );
}
