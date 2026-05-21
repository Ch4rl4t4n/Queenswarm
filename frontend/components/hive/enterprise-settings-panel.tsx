"use client";

import { DownloadIcon, Loader2Icon, ShieldCheckIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";
import type { EnterpriseWorkspaceView } from "@/lib/hive-types";

export function EnterpriseSettingsPanel(): JSX.Element | null {
  const { hasFeature, refresh } = usePlatform();
  const [config, setConfig] = useState<EnterpriseWorkspaceView | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [brandName, setBrandName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [accentHex, setAccentHex] = useState("#FFB800");
  const [hideBranding, setHideBranding] = useState(false);
  const [customDomain, setCustomDomain] = useState("");
  const [retentionDays, setRetentionDays] = useState("365");
  const [complianceEmail, setComplianceEmail] = useState("");
  const [soc2Url, setSoc2Url] = useState("");
  const [monthlyExport, setMonthlyExport] = useState(false);
  const [hiveNote, setHiveNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<EnterpriseWorkspaceView>("settings/enterprise/config");
      setConfig(payload);
      setBrandName(payload.white_label.brand_name ?? "");
      setLogoUrl(payload.white_label.logo_url ?? "");
      setAccentHex(payload.white_label.accent_hex);
      setHideBranding(payload.white_label.hide_platform_branding);
      setCustomDomain(payload.white_label.custom_domain ?? "");
      setRetentionDays(String(payload.compliance.data_retention_days));
      setComplianceEmail(payload.compliance.compliance_contact_email ?? "");
      setSoc2Url(payload.compliance.soc2_attestation_url ?? "");
      setMonthlyExport(payload.compliance.monthly_audit_export);
      setHiveNote(payload.compliance.dedicated_hive_note ?? "");
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Enterprise workspace unavailable.");
      setConfig(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasFeature("enterprise_workspace")) return;
    void load();
  }, [hasFeature, load]);

  const save = useCallback(async () => {
    setBusy(true);
    try {
      const payload = await hivePatchJson<EnterpriseWorkspaceView>("settings/enterprise/config", {
        white_label: {
          brand_name: brandName.trim() || null,
          logo_url: logoUrl.trim() || null,
          accent_hex: accentHex,
          hide_platform_branding: hideBranding,
          custom_domain: customDomain.trim() || null,
        },
        compliance: {
          data_retention_days: Math.max(30, Math.min(2555, Number(retentionDays) || 365)),
          compliance_contact_email: complianceEmail.trim() || null,
          soc2_attestation_url: soc2Url.trim() || null,
          monthly_audit_export: monthlyExport,
          dedicated_hive_note: hiveNote.trim() || null,
        },
      });
      setConfig(payload);
      toast.success("Enterprise workspace saved.");
      setErr(null);
      await refresh();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Save failed.";
      setErr(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }, [
    accentHex,
    brandName,
    complianceEmail,
    customDomain,
    hideBranding,
    hiveNote,
    logoUrl,
    monthlyExport,
    refresh,
    retentionDays,
    soc2Url,
  ]);

  const downloadBundle = useCallback(async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/proxy/settings/enterprise/compliance-export/download", { cache: "no-store" });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(String((json as { detail?: string }).detail ?? "Export failed."));
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `queenswarm-compliance-${config?.tenant_id ?? "tenant"}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Compliance bundle downloaded.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  }, [config?.tenant_id]);

  if (!hasFeature("enterprise_workspace")) {
    return (
      <V4Card>
        <V4CardHeader
          title="Enterprise workspace"
          description="White-label branding and compliance profile require Enterprise tier on commercial workspaces."
        />
        <p className="text-sm text-(--qs-text-3)">
          Upgrade via{" "}
          <Link href="/settings/billing" className="text-pollen hover:underline">
            Billing
          </Link>{" "}
          or contact your operator for internal hive access.
        </p>
      </V4Card>
    );
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading enterprise workspace…
      </p>
    );
  }

  const ha = config?.ha_profile;
  const brandingLocked = config ? !config.custom_branding_allowed : false;

  return (
    <div className="space-y-6">
      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      <V4Card>
        <V4CardHeader
          kicker="White-label"
          title="Dedicated hive branding"
          description="Logo, accent, and optional custom domain — verified workflows only reach users after simulation."
          actions={
            brandingLocked ? (
              <V4Badge tone="warn">Enterprise tier required</V4Badge>
            ) : (
              <V4Badge tone="ok">Branding unlocked</V4Badge>
            )
          }
        />

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="block space-y-1 text-sm">
            <span className="text-(--qs-text-3)">Brand name</span>
            <input
              className="v4-input w-full"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              disabled={brandingLocked || busy}
              placeholder="Acme Hive"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-(--qs-text-3)">Logo URL (HTTPS)</span>
            <input
              className="v4-input w-full"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              disabled={brandingLocked || busy}
              placeholder="https://cdn.example.com/logo.svg"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-(--qs-text-3)">Accent hex</span>
            <input
              className="v4-input w-full font-mono"
              value={accentHex}
              onChange={(e) => setAccentHex(e.target.value)}
              disabled={brandingLocked || busy}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-(--qs-text-3)">Custom domain</span>
            <input
              className="v4-input w-full"
              value={customDomain}
              onChange={(e) => setCustomDomain(e.target.value)}
              disabled={brandingLocked || busy}
              placeholder="hive.yourcompany.com"
            />
            {config?.white_label.custom_domain ? (
              <span className="text-xs text-(--qs-text-3)">
                DNS status: {config.white_label.custom_domain_status}
              </span>
            ) : null}
          </label>
        </div>

        <label className="mt-4 flex items-center gap-2 text-sm text-(--qs-text-2)">
          <input
            type="checkbox"
            checked={hideBranding}
            onChange={(e) => setHideBranding(e.target.checked)}
            disabled={brandingLocked || busy}
          />
          Hide Queenswarm platform branding in customer-facing surfaces
        </label>

        <div
          className="mt-4 rounded-xl border border-(--qs-border) p-4"
          style={{ boxShadow: `0 0 24px ${accentHex}33` }}
        >
          <p className="text-xs uppercase tracking-widest text-(--qs-text-3)">Preview</p>
          <div className="mt-2 flex items-center gap-3">
            {logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={logoUrl} alt="" className="h-8 w-8 rounded-lg object-contain" />
            ) : (
              <span className="text-2xl" aria-hidden>
                🐝
              </span>
            )}
            <span className="font-[family-name:var(--font-space-grotesk)] text-lg" style={{ color: accentHex }}>
              {brandName.trim() || config?.tenant_name || "Your hive"}
            </span>
          </div>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Compliance"
          title="Enterprise compliance profile"
          description="Retention, SOC2 attestation link, and monthly audit export scheduling."
          actions={
            <V4Badge tone="info">
              <ShieldCheckIcon className="mr-1 inline h-3 w-3" aria-hidden /> audit-ready
            </V4Badge>
          }
        />

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="block space-y-1 text-sm">
            <span className="text-(--qs-text-3)">Data retention (days)</span>
            <input
              className="v4-input w-full"
              type="number"
              min={30}
              max={2555}
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
              disabled={busy}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-(--qs-text-3)">Compliance contact email</span>
            <input
              className="v4-input w-full"
              type="email"
              value={complianceEmail}
              onChange={(e) => setComplianceEmail(e.target.value)}
              disabled={busy}
            />
          </label>
          <label className="block space-y-1 text-sm md:col-span-2">
            <span className="text-(--qs-text-3)">SOC2 / ISO attestation URL</span>
            <input
              className="v4-input w-full"
              value={soc2Url}
              onChange={(e) => setSoc2Url(e.target.value)}
              disabled={busy}
              placeholder="https://trust.example.com/soc2"
            />
          </label>
          <label className="block space-y-1 text-sm md:col-span-2">
            <span className="text-(--qs-text-3)">Dedicated hive note (internal)</span>
            <textarea
              className="v4-input min-h-[72px] w-full"
              value={hiveNote}
              onChange={(e) => setHiveNote(e.target.value)}
              disabled={busy}
              placeholder="Single-tenant VPC, EU data residency, etc."
            />
          </label>
        </div>

        <label className="mt-4 flex items-center gap-2 text-sm text-(--qs-text-2)">
          <input
            type="checkbox"
            checked={monthlyExport}
            onChange={(e) => setMonthlyExport(e.target.checked)}
            disabled={busy}
          />
          Schedule monthly compliance export (digest rail uses Audit settings)
        </label>

        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" className="v4-btn v4-btn--primary" onClick={() => void save()} disabled={busy}>
            {busy ? "Saving…" : "Save workspace"}
          </button>
          <button type="button" className="v4-btn v4-btn--ghost" onClick={() => void downloadBundle()} disabled={busy}>
            <DownloadIcon className="mr-1 inline h-4 w-4" aria-hidden />
            Download compliance bundle
          </button>
          <Link href="/settings/audit" className="v4-btn v4-btn--ghost">
            Open audit log
          </Link>
        </div>
      </V4Card>

      {ha ? (
        <V4Card>
          <V4CardHeader
            kicker="HA profile"
            title={ha.profile_label}
            description="Read-only deployment signals — run scripts/dr-drill.sh and scripts/ha-chaos-smoke.sh for evidence."
          />
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <HaSignal label="HA mode" ok={ha.ha_mode_enabled} />
            <HaSignal label="Redis failover" ok={ha.redis_failover_configured} />
            <HaSignal label="Postgres replica" ok={ha.postgres_replica_configured} />
            <HaSignal label="DR drill script" ok={ha.backup_drill_script_available} />
          </div>
          {ha.dr_drill?.report_available ? (
            <div className="mt-4 rounded-lg border border-(--qs-green)/30 bg-(--qs-green)/5 px-3 py-2 text-sm">
              <p className="font-medium text-(--qs-green)">Latest DR drill evidence</p>
              <p className="mt-1 text-(--qs-text-3)">
                {ha.dr_drill.last_drill_at ? `UTC ${ha.dr_drill.last_drill_at}` : "Timestamp pending"} · backup{" "}
                {ha.dr_drill.backup_duration_sec ?? "—"}s · {ha.dr_drill.restore_status ?? "unknown"}
              </p>
              {ha.dr_drill.report_file ? (
                <p className="mt-1 font-mono text-xs text-(--qs-text-3)">{ha.dr_drill.report_file}</p>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-xs text-(--qs-text-3)">
              No DR drill report mounted yet — run <code className="font-mono">./scripts/dr-drill.sh</code> on the
              host and mount <code className="font-mono">reports/dr</code> into the backend container.
            </p>
          )}
          {ha.ha_chaos?.report_available ? (
            <div className="mt-4 rounded-lg border border-cyan/30 bg-cyan/5 px-3 py-2 text-sm">
              <p className="font-medium text-cyan">
                Latest HA chaos drill {ha.ha_chaos.passed ? "passed" : "failed"}
              </p>
              <p className="mt-1 text-(--qs-text-3)">
                {ha.ha_chaos.last_drill_at ? `UTC ${ha.ha_chaos.last_drill_at}` : "Timestamp pending"} · baseline{" "}
                {ha.ha_chaos.baseline_ready_code ?? "—"} → degraded {ha.ha_chaos.degraded_ready_code ?? "—"} →
                recovered {ha.ha_chaos.recovered_ready_code ?? "—"}
              </p>
              {ha.ha_chaos.report_file ? (
                <p className="mt-1 font-mono text-xs text-(--qs-text-3)">{ha.ha_chaos.report_file}</p>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-xs text-(--qs-text-3)">
              No HA chaos evidence yet — quarterly run:{" "}
              <code className="font-mono">./scripts/ha-chaos-smoke.sh</code>
            </p>
          )}
          <p className="mt-3 font-mono text-sm text-pollen">{ha.readiness_pct}% readiness</p>
        </V4Card>
      ) : null}
    </div>
  );
}

function HaSignal({ label, ok }: { label: string; ok: boolean }): JSX.Element {
  return (
    <div className="rounded-lg border border-(--qs-border) bg-black/25 px-3 py-2">
      <p className="text-xs text-(--qs-text-3)">{label}</p>
      <p className={ok ? "text-(--qs-green)" : "text-(--qs-text-3)"}>{ok ? "Configured" : "Not configured"}</p>
    </div>
  );
}
