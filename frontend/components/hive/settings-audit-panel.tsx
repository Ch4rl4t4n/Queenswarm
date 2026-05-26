"use client";

import { Download } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { SettingsAuditGrid, SettingsAuditGridSkeleton } from "@/components/hive/settings-audit-grid";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import {
  filterAuditRows,
  formatAuditTime,
  type AuditFilter,
  type TenantAuditLogRow,
} from "@/lib/settings-audit-utils";

interface TeamMemberRow {
  user_id: string;
  email: string;
}

interface TeamOverviewResponse {
  members: TeamMemberRow[];
}

interface AuditDigestConfig {
  enabled: boolean;
  enabled_override: boolean | null;
  window_hours: number;
  window_hours_override: number | null;
  schedule_hour_utc: number;
  schedule_hour_override: number | null;
  extra_recipients: string[];
  slack_webhook_configured: boolean;
  slack_webhook_preview: string | null;
  discord_webhook_configured: boolean;
  discord_webhook_preview: string | null;
  teams_webhook_configured: boolean;
  teams_webhook_preview: string | null;
  last_sent_at: string | null;
  global_enabled: boolean;
  global_window_hours: number;
  global_schedule_hour_utc: number;
}

interface SessionPlaybookConfig {
  auto_save_on_approve: boolean;
  auto_save_on_approve_override: boolean | null;
  mark_verified_on_auto_save: boolean;
  mark_verified_on_auto_save_override: boolean | null;
  recipes_enabled: boolean;
}

export function SettingsAuditPanel() {
  const [rows, setRows] = useState<TenantAuditLogRow[] | null>(null);
  const [memberMap, setMemberMap] = useState<Map<string, string>>(new Map());
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<AuditFilter>("all");
  const [digestBusy, setDigestBusy] = useState(false);
  const [digestConfig, setDigestConfig] = useState<AuditDigestConfig | null>(null);
  const [digestConfigBusy, setDigestConfigBusy] = useState(false);
  const [digestWebhookTestBusy, setDigestWebhookTestBusy] = useState(false);
  const [digestEnabled, setDigestEnabled] = useState(true);
  const [digestWindowHours, setDigestWindowHours] = useState("24");
  const [digestScheduleHour, setDigestScheduleHour] = useState("7");
  const [digestExtraRecipients, setDigestExtraRecipients] = useState("");
  const [digestSlackWebhook, setDigestSlackWebhook] = useState("");
  const [clearSlackWebhook, setClearSlackWebhook] = useState(false);
  const [digestDiscordWebhook, setDigestDiscordWebhook] = useState("");
  const [clearDiscordWebhook, setClearDiscordWebhook] = useState(false);
  const [digestTeamsWebhook, setDigestTeamsWebhook] = useState("");
  const [clearTeamsWebhook, setClearTeamsWebhook] = useState(false);
  const [playbookConfig, setPlaybookConfig] = useState<SessionPlaybookConfig | null>(null);
  const [playbookConfigBusy, setPlaybookConfigBusy] = useState(false);
  const [autoSavePlaybook, setAutoSavePlaybook] = useState(false);
  const [autoSaveMarkVerified, setAutoSaveMarkVerified] = useState(true);

  const load = useCallback(async () => {
    try {
      const [auditRows, team, digestCfg, playbookCfg] = await Promise.all([
        hiveGet<TenantAuditLogRow[]>("settings/team/audit-logs"),
        hiveGet<TeamOverviewResponse>("settings/team").catch(() => ({ members: [] as TeamMemberRow[] })),
        hiveGet<AuditDigestConfig>("settings/team/audit-digest/config").catch(() => null),
        hiveGet<SessionPlaybookConfig>("settings/team/session-playbook/config").catch(() => null),
      ]);
      setRows(auditRows);
      const map = new Map<string, string>();
      for (const m of team.members ?? []) {
        map.set(m.user_id, m.email);
      }
      setMemberMap(map);
      if (digestCfg) {
        setDigestConfig(digestCfg);
        setDigestEnabled(digestCfg.enabled_override ?? digestCfg.enabled);
        setDigestWindowHours(String(digestCfg.window_hours_override ?? digestCfg.window_hours));
        setDigestScheduleHour(String(digestCfg.schedule_hour_override ?? digestCfg.schedule_hour_utc));
        setDigestExtraRecipients((digestCfg.extra_recipients ?? []).join("\n"));
        setDigestSlackWebhook("");
        setClearSlackWebhook(false);
        setDigestDiscordWebhook("");
        setClearDiscordWebhook(false);
        setDigestTeamsWebhook("");
        setClearTeamsWebhook(false);
      }
      if (playbookCfg) {
        setPlaybookConfig(playbookCfg);
        setAutoSavePlaybook(playbookCfg.auto_save_on_approve_override ?? playbookCfg.auto_save_on_approve);
        setAutoSaveMarkVerified(
          playbookCfg.mark_verified_on_auto_save_override ?? playbookCfg.mark_verified_on_auto_save,
        );
      }
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Load failed";
      setErr(msg);
      setRows([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => filterAuditRows(rows ?? [], filter), [filter, rows]);

  function exportJson(): void {
    if (!filtered.length) {
      toast.message("Nothing to export for the current filter.");
      return;
    }
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `queenswarm-audit-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Audit log exported.");
  }

  async function sendSupervisorDigest(): Promise<void> {
    setDigestBusy(true);
    try {
      const result = await hivePostJson<{
        sent: boolean;
        reason?: string | null;
        sent_count?: number;
        action_count?: number;
        slack_sent?: boolean;
        discord_sent?: boolean;
        teams_sent?: boolean;
      }>("settings/team/audit-digest/send", {});
      if (result.sent) {
        const channels = [
          (result.sent_count ?? 0) > 0 ? "email" : null,
          result.slack_sent ? "Slack" : null,
          result.discord_sent ? "Discord" : null,
          result.teams_sent ? "Teams" : null,
        ]
          .filter(Boolean)
          .join(" + ");
        toast.success(
          `Supervisor audit digest sent via ${channels || "configured channels"} (${result.action_count ?? 0} actions).`,
        );
        const updated = await hiveGet<AuditDigestConfig>("settings/team/audit-digest/config").catch(() => null);
        if (updated) {
          setDigestConfig(updated);
        }
      } else {
        toast.message(result.reason ?? "Digest not sent.");
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Digest send failed");
    } finally {
      setDigestBusy(false);
    }
  }

  async function saveDigestConfig(): Promise<void> {
    const windowHours = Number.parseInt(digestWindowHours, 10);
    const scheduleHour = Number.parseInt(digestScheduleHour, 10);
    if (!Number.isFinite(windowHours) || windowHours < 1 || windowHours > 168) {
      toast.error("Window hours must be between 1 and 168.");
      return;
    }
    if (!Number.isFinite(scheduleHour) || scheduleHour < 0 || scheduleHour > 23) {
      toast.error("Schedule hour must be between 0 and 23 UTC.");
      return;
    }
    const extraRecipients = digestExtraRecipients
      .split(/[\n,;]+/)
      .map((item) => item.trim())
      .filter(Boolean);

    setDigestConfigBusy(true);
    try {
      const updated = await hivePatchJson<AuditDigestConfig>("settings/team/audit-digest/config", {
        enabled: digestEnabled,
        window_hours: windowHours,
        schedule_hour_utc: scheduleHour,
        extra_recipients: extraRecipients,
        slack_webhook_url: digestSlackWebhook.trim() || undefined,
        clear_slack_webhook: clearSlackWebhook,
        discord_webhook_url: digestDiscordWebhook.trim() || undefined,
        clear_discord_webhook: clearDiscordWebhook,
        teams_webhook_url: digestTeamsWebhook.trim() || undefined,
        clear_teams_webhook: clearTeamsWebhook,
      });
      setDigestConfig(updated);
      setDigestSlackWebhook("");
      setClearSlackWebhook(false);
      setDigestDiscordWebhook("");
      setClearDiscordWebhook(false);
      setDigestTeamsWebhook("");
      setClearTeamsWebhook(false);
      toast.success("Supervisor digest schedule saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Failed to save digest config");
    } finally {
      setDigestConfigBusy(false);
    }
  }

  async function testDigestWebhooks(): Promise<void> {
    setDigestWebhookTestBusy(true);
    try {
      const result = await hivePostJson<{
        slack?: boolean;
        discord?: boolean;
        teams?: boolean;
        detail?: string | null;
      }>("settings/team/audit-digest/test-webhooks", {});
      if (result.detail === "no_webhooks_accepted") {
        toast.message("No digest webhooks accepted the test (configure tenant or platform URLs first).");
        return;
      }
      const channels = [
        result.slack ? "Slack" : null,
        result.discord ? "Discord" : null,
        result.teams ? "Teams" : null,
      ]
        .filter(Boolean)
        .join(" + ");
      toast.success(`Digest webhook test sent via ${channels || "configured channels"}.`);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Webhook test failed");
    } finally {
      setDigestWebhookTestBusy(false);
    }
  }

  async function savePlaybookConfig(): Promise<void> {
    setPlaybookConfigBusy(true);
    try {
      const updated = await hivePatchJson<SessionPlaybookConfig>("settings/team/session-playbook/config", {
        auto_save_on_approve: autoSavePlaybook,
        mark_verified_on_auto_save: autoSaveMarkVerified,
      });
      setPlaybookConfig(updated);
      toast.success("Session playbook automation saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Failed to save playbook config");
    } finally {
      setPlaybookConfigBusy(false);
    }
  }

  return (
    <>
    <V4Card>
      <V4CardHeader
        title="Audit log"
        description="Admin actions, key rotations, hive auto-rebalances · 60-day retention."
      />
      <div className="v4-toolbar-row">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={digestBusy}
          onClick={() => void sendSupervisorDigest()}
        >
          {digestBusy ? "Sending…" : "Supervisor digest"}
        </button>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5" onClick={() => exportJson()}>
          <Download className="h-3.5 w-3.5" aria-hidden />
          Export
        </button>
        <QsSelect
          className="w-[140px] py-2 text-sm"
          value={filter}
          onValueChange={(next) => setFilter(next as AuditFilter)}
          aria-label="Filter audit actions"
          options={[
            { value: "all", label: "All actions" },
            { value: "auth", label: "Auth" },
            { value: "keys", label: "Keys" },
            { value: "team", label: "Team" },
            { value: "sharing", label: "Sharing" },
          ]}
        />
      </div>

      {err ? (
        <p className="mt-4 rounded-xl border border-danger/30 bg-danger/6 px-4 py-3 text-sm text-danger" role="alert">
          {err}
        </p>
      ) : null}

      {!rows ? (
        <SettingsAuditGridSkeleton />
      ) : filtered.length === 0 ? (
        <p className="mt-6 text-sm text-(--qs-text-3)">No audit entries yet for this filter.</p>
      ) : (
        <SettingsAuditGrid rows={filtered} memberMap={memberMap} />
      )}

      {rows && rows.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <V4Badge tone="info">{filtered.length} entries</V4Badge>
          <span className="text-xs text-(--qs-text-3)">Requires team:manage permission</span>
        </div>
      ) : null}
    </V4Card>

    <V4Card className="mt-6">
      <V4CardHeader
        title="Supervisor digest schedule"
        description="Per-tenant email, Slack, Discord, and Teams summary of operator session actions. Owners/admins always receive mail unless opted out in notification prefs."
      />

      {!digestConfig ? (
        <div className="mt-4 h-24 animate-pulse rounded-xl bg-white/4" />
      ) : (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-(--qs-text-2)">Scheduled digests</span>
            <QsSelect
              value={digestEnabled ? "on" : "off"}
              onValueChange={(next) => setDigestEnabled(next === "on")}
              aria-label="Enable scheduled supervisor digests"
              options={[
                { value: "on", label: "Enabled for this tenant" },
                { value: "off", label: "Disabled for this tenant" },
              ]}
            />
            <span className="text-xs text-(--qs-text-3)">
              Platform default: {digestConfig.global_enabled ? "on" : "off"} · last sent{" "}
              {digestConfig.last_sent_at ? formatAuditTime(digestConfig.last_sent_at) : "never"}
            </span>
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-(--qs-text-2)">Window (hours)</span>
            <input
              type="number"
              min={1}
              max={168}
              className="qs-input"
              value={digestWindowHours}
              onChange={(e) => setDigestWindowHours(e.target.value)}
            />
            <span className="text-xs text-(--qs-text-3)">
              Global default: {digestConfig.global_window_hours}h
            </span>
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-(--qs-text-2)">Send at (UTC hour)</span>
            <QsSelect
              value={digestScheduleHour}
              onValueChange={setDigestScheduleHour}
              aria-label="Digest schedule hour UTC"
              options={Array.from({ length: 24 }, (_, hour) => ({
                value: String(hour),
                label: `${String(hour).padStart(2, "0")}:00 UTC`,
              }))}
            />
            <span className="text-xs text-(--qs-text-3)">
              Default: {String(digestConfig.global_schedule_hour_utc).padStart(2, "0")}:00 UTC
            </span>
          </label>

          <label className="flex flex-col gap-1.5 text-sm md:col-span-2">
            <span className="text-(--qs-text-2)">Extra recipients (one email per line)</span>
            <textarea
              className="qs-input min-h-[88px] resize-y font-mono text-xs"
              value={digestExtraRecipients}
              onChange={(e) => setDigestExtraRecipients(e.target.value)}
              placeholder="ops@acme.com"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-sm md:col-span-2">
            <span className="text-(--qs-text-2)">Slack webhook override (optional)</span>
            <input
              type="url"
              className="qs-input font-mono text-xs"
              value={digestSlackWebhook}
              onChange={(e) => setDigestSlackWebhook(e.target.value)}
              placeholder={
                digestConfig.slack_webhook_configured
                  ? `Configured: ${digestConfig.slack_webhook_preview ?? "…"}`
                  : "https://hooks.slack.com/services/…"
              }
            />
            {digestConfig.slack_webhook_configured ? (
              <label className="inline-flex items-center gap-2 text-xs text-(--qs-text-3)">
                <input
                  type="checkbox"
                  checked={clearSlackWebhook}
                  onChange={(e) => setClearSlackWebhook(e.target.checked)}
                />
                Remove tenant webhook (use platform Slack URL)
              </label>
            ) : null}
          </label>

          <label className="flex flex-col gap-1.5 text-sm md:col-span-2">
            <span className="text-(--qs-text-2)">Discord webhook override (optional)</span>
            <input
              type="url"
              className="qs-input font-mono text-xs"
              value={digestDiscordWebhook}
              onChange={(e) => setDigestDiscordWebhook(e.target.value)}
              placeholder={
                digestConfig.discord_webhook_configured
                  ? `Configured: ${digestConfig.discord_webhook_preview ?? "…"}`
                  : "https://discord.com/api/webhooks/…"
              }
            />
            {digestConfig.discord_webhook_configured ? (
              <label className="inline-flex items-center gap-2 text-xs text-(--qs-text-3)">
                <input
                  type="checkbox"
                  checked={clearDiscordWebhook}
                  onChange={(e) => setClearDiscordWebhook(e.target.checked)}
                />
                Remove tenant webhook (use platform Discord URL)
              </label>
            ) : null}
          </label>

          <label className="flex flex-col gap-1.5 text-sm md:col-span-2">
            <span className="text-(--qs-text-2)">Microsoft Teams webhook override (optional)</span>
            <input
              type="url"
              className="qs-input font-mono text-xs"
              value={digestTeamsWebhook}
              onChange={(e) => setDigestTeamsWebhook(e.target.value)}
              placeholder={
                digestConfig.teams_webhook_configured
                  ? `Configured: ${digestConfig.teams_webhook_preview ?? "…"}`
                  : "https://outlook.office.com/webhook/…"
              }
            />
            {digestConfig.teams_webhook_configured ? (
              <label className="inline-flex items-center gap-2 text-xs text-(--qs-text-3)">
                <input
                  type="checkbox"
                  checked={clearTeamsWebhook}
                  onChange={(e) => setClearTeamsWebhook(e.target.checked)}
                />
                Remove tenant webhook (use platform Teams URL)
              </label>
            ) : null}
          </label>

          <div className="md:col-span-2 flex flex-wrap gap-2 max-lg:flex-col max-lg:gap-3">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm max-lg:w-full"
              disabled={digestConfigBusy}
              onClick={() => void saveDigestConfig()}
            >
              {digestConfigBusy ? "Saving…" : "Save digest schedule"}
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm max-lg:self-end"
              disabled={digestWebhookTestBusy || digestConfigBusy}
              onClick={() => void testDigestWebhooks()}
            >
              {digestWebhookTestBusy ? "Testing…" : "Test webhooks"}
            </button>
          </div>
        </div>
      )}
    </V4Card>

    <V4Card className="mt-6">
      <V4CardHeader
        title="Session playbook automation"
        description="When enabled, approving a supervisor session auto-saves an operator playbook to the Recipe Library (fail-soft if the session is not ready)."
      />

      {!playbookConfig ? (
        <div className="mt-4 h-20 animate-pulse rounded-xl bg-white/4" />
      ) : (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-(--qs-text-2)">Auto-save on approve</span>
            <QsSelect
              value={autoSavePlaybook ? "on" : "off"}
              onValueChange={(next) => setAutoSavePlaybook(next === "on")}
              aria-label="Auto-save playbook on session approve"
              options={[
                { value: "on", label: "Enabled for this tenant" },
                { value: "off", label: "Disabled (manual save only)" },
              ]}
            />
            <span className="text-xs text-(--qs-text-3)">
              Recipe Library module: {playbookConfig.recipes_enabled ? "enabled" : "disabled globally"}
            </span>
          </label>

          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-(--qs-text-2)">Mark auto-saved playbooks verified</span>
            <QsSelect
              value={autoSaveMarkVerified ? "on" : "off"}
              onValueChange={(next) => setAutoSaveMarkVerified(next === "on")}
              aria-label="Mark auto-saved playbooks as verified"
              options={[
                { value: "on", label: "Stamp verified when eligible" },
                { value: "off", label: "Save as draft only" },
              ]}
            />
          </label>

          <div className="md:col-span-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={playbookConfigBusy || !playbookConfig.recipes_enabled}
              onClick={() => void savePlaybookConfig()}
            >
              {playbookConfigBusy ? "Saving…" : "Save playbook automation"}
            </button>
          </div>
        </div>
      )}
    </V4Card>
    </>
  );
}
