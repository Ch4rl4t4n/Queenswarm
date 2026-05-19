"use client";

import type { ChangeEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Copy, RefreshCw } from "lucide-react";

import { QsSelect } from "@/components/ui/qs-select";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { V4Badge, V4Card, V4CardHeader, V4PageCanvas } from "@/components/ui/v4";
import { COCKPIT_POLL_EXTERNAL_METRICS_MS } from "@/lib/cockpit-poll-profile";
import { cn } from "@/lib/utils";

interface ExternalProjectRow {
  id: string;
  slug: string;
  display_name: string;
  project_kind: string;
  settings: Record<string, unknown>;
  webhook_url: string | null;
  is_active: boolean;
}

interface ExternalMetricsBundle {
  metrics: {
    runs_total: number;
    runs_success: number;
    success_rate: number;
    cost_usd_total: number;
  };
  series: Array<{
    t: string;
    ok: boolean;
    latency_ms: number;
    cost_usd: number;
    action: string;
  }>;
}

interface ExternalApiKeyMinted {
  id: string;
  plaintext_key: string;
}

function kindBadgeTone(kind: string): "info" | "gold" | "purple" {
  const k = kind.toLowerCase();
  if (k === "trading") return "info";
  if (k === "food_ordering") return "gold";
  return "purple";
}

export function ExternalProjectsConsole() {
  const [projects, setProjects] = useState<ExternalProjectRow[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<ExternalMetricsBundle | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [metricsFetchMode, setMetricsFetchMode] = useState<"idle" | "initial" | "poll">("idle");

  const [slug, setSlug] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [projectKind, setProjectKind] = useState<"trading" | "food_ordering" | "generic">("generic");
  const [settingsJson, setSettingsJson] = useState("{}");
  const [createBusy, setCreateBusy] = useState(false);

  const [keyLabel, setKeyLabel] = useState("");
  const [permissionsText, setPermissionsText] = useState("run");
  const [mintedKey, setMintedKey] = useState<string | null>(null);
  const [mintBusy, setMintBusy] = useState(false);

  const refreshProjects = useCallback(async () => {
    setLoadError(null);
    try {
      const rows = await hiveGet<ExternalProjectRow[]>("external/projects");
      setProjects(rows);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Failed to load projects.";
      setLoadError(msg);
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    if (selectedId !== null) {
      return;
    }
    setSelectedId((current) => {
      if (current !== null) {
        return current;
      }
      const first = projects?.[0]?.id;
      return first ?? null;
    });
  }, [projects, selectedId]);

  const loadMetrics = useCallback(async (projectId: string, mode: "initial" | "poll") => {
    setMetricsFetchMode(mode === "poll" ? "poll" : "initial");
    setMetricsError(null);
    try {
      const m = await hiveGet<ExternalMetricsBundle>(`external/projects/${projectId}/metrics`);
      setMetrics(m);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Metrics unavailable.";
      setMetricsError(msg);
      setMetrics(null);
    } finally {
      setMetricsFetchMode("idle");
    }
  }, []);

  useEffect(() => {
    if (selectedId) {
      void loadMetrics(selectedId, "initial");
    }
  }, [selectedId, loadMetrics]);

  useEffect(() => {
    if (!selectedId) {
      return undefined;
    }
    const id = selectedId;
    const handle = window.setInterval(() => void loadMetrics(id, "poll"), COCKPIT_POLL_EXTERNAL_METRICS_MS);
    return () => window.clearInterval(handle);
  }, [selectedId, loadMetrics]);

  const selected = useMemo(
    () => projects?.find((p) => p.id === selectedId) ?? null,
    [projects, selectedId],
  );

  const lineData = useMemo(() => {
    if (!metrics?.series.length) return [];
    return metrics.series.map((row, idx) => ({
      idx,
      latency_ms: row.latency_ms,
      okLabel: row.ok ? "pass" : "fail",
      action: row.action,
      shortT: row.t.slice(11, 19),
    }));
  }, [metrics]);

  const barData = useMemo(() => {
    if (!metrics?.series.length) return [];
    let ok = 0;
    let fail = 0;
    for (const row of metrics.series) {
      if (row.ok) ok += 1;
      else fail += 1;
    }
    return [
      { name: "verified_ok", count: ok, fill: "#00FF88" },
      { name: "blocked_or_err", count: fail, fill: "#FF3366" },
    ];
  }, [metrics]);

  async function handleCreate(): Promise<void> {
    setCreateBusy(true);
    try {
      let parsedSettings: Record<string, unknown> = {};
      try {
        parsedSettings = JSON.parse(settingsJson || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("Settings JSON is invalid.");
      }
      await hivePostJson<ExternalProjectRow>("external/projects", {
        slug,
        display_name: displayName,
        project_kind: projectKind,
        settings: parsedSettings,
        webhook_url: null,
        webhook_secret: null,
      });
      setSlug("");
      setDisplayName("");
      setSettingsJson("{}");
      await refreshProjects();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Create failed.";
      setLoadError(msg);
    } finally {
      setCreateBusy(false);
    }
  }

  async function handleMintKey(): Promise<void> {
    if (!selectedId) return;
    setMintBusy(true);
    setMintedKey(null);
    try {
      const scopes = permissionsText
        .split(/[, ]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const minted = await hivePostJson<ExternalApiKeyMinted>(`external/projects/${selectedId}/api-keys`, {
        label: keyLabel || null,
        permissions: scopes.length ? scopes : ["run"],
      });
      setMintedKey(minted.plaintext_key);
      void loadMetrics(selectedId, "initial");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Mint failed.";
      setMetricsError(msg);
    } finally {
      setMintBusy(false);
    }
  }

  async function copyText(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* HTTPS clipboard gate */
    }
  }

  const inputClass = "qs-input min-h-10 w-full";

  return (
    <V4PageCanvas className="pb-16 pt-2">
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="v4-field-label text-(--qs-magenta)">Phase 2.5 · Integration layer</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-(--qs-text) md:text-4xl">External projects</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-(--qs-text-3)">
            Register MCP-first integrations with scoped <span className="font-mono text-pollen">qs_ep_</span> keys, REST{" "}
            <code className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[12px] text-pollen">{`/external/{slug}/run`}</code>, and WebSocket
            lanes — mirrored into HiveMind vault audit stitches when enabled.
          </p>
        </div>
        <button type="button" onClick={() => void refreshProjects()} className="qs-btn qs-btn--ghost gap-2">
          <RefreshCw className="h-4 w-4" aria-hidden />
          Refresh registry
        </button>
      </header>

      {loadError ? (
        <div className="rounded-2xl border border-[#FF3366]/40 bg-[#FF3366]/10 px-4 py-3 text-sm text-[#ffb8c8]" role="alert">
          {loadError}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <V4Card>
          <V4CardHeader title="Register bridge" description="Mint secrets once — external vaulting stays operator-owned." />

          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <label htmlFor="ep-slug" className="v4-field-label">
                Slug
              </label>
              <input
                id="ep-slug"
                value={slug}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setSlug(e.target.value)}
                placeholder="my-trading-bot"
                className={cn(inputClass, "font-mono text-cyan")}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="ep-name" className="v4-field-label">
                Display name
              </label>
              <input
                id="ep-name"
                value={displayName}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDisplayName(e.target.value)}
                placeholder="Paper swarm trader"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="ep-kind" className="v4-field-label">
                Lane template
              </label>
              <QsSelect
                id="ep-kind"
                value={projectKind}
                onValueChange={(next) => setProjectKind(next as typeof projectKind)}
                className={inputClass}
                options={[
                  { value: "generic", label: "Generic simulate / echo" },
                  { value: "trading", label: "Trading risk rails" },
                  { value: "food_ordering", label: "Food ordering cart" },
                ]}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="ep-settings" className="v4-field-label">
                Settings JSON
              </label>
              <textarea
                id="ep-settings"
                value={settingsJson}
                onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setSettingsJson(e.target.value)}
                rows={5}
                spellCheck={false}
                className="v4-textarea w-full font-mono text-[12px]"
              />
              <p className="text-[11px] text-zinc-500">
                Trading example:{" "}
                <code className="font-mono text-cyan">{`{"trading_mode":"paper","max_order_usd":2500,"max_daily_loss_usd":500,"max_risk_pct_per_trade":2,"watchlist":["BTC","ETH"],"paper_trading_auto_tick":true}`}</code>
              </p>
            </div>
            <button
              type="button"
              disabled={createBusy || !slug.trim() || !displayName.trim()}
              onClick={() => void handleCreate()}
              className="qs-btn qs-btn--primary w-full disabled:opacity-40"
            >
              {createBusy ? "Provisioning…" : "Create project"}
            </button>
          </div>
        </V4Card>

        <div className="space-y-6">
          <V4Card>
            <V4CardHeader title="Registry" description="Active bridges owned by this dashboard session." />

            <div className="mt-4 space-y-3">
              {!projects?.length ? (
                <p className="text-sm text-zinc-500">No projects yet — stage one on the left.</p>
              ) : (
                <ul className="space-y-2">
                  {projects.map((p) => {
                    const active = p.id === selectedId;
                    return (
                      <li key={p.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedId(p.id)}
                          className={cn(
                            "flex w-full flex-col gap-1 rounded-2xl border px-4 py-3 text-left transition",
                            active ? "v4-dream-cycle-card border-pollen/45 bg-pollen/[0.06]" : "v4-session-row border-transparent hover:border-(--qs-border)",
                          )}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-[family-name:var(--font-space-grotesk)] text-[15px] font-semibold text-white">
                              {p.display_name}
                            </span>
                            <V4Badge tone={kindBadgeTone(p.project_kind)}>{p.project_kind}</V4Badge>
                          </div>
                          <div className="font-mono text-xs text-(--qs-text-3)">{p.slug}</div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </V4Card>

          {selected ? (
            <>
              <V4Card>
                <V4CardHeader
                  title="Scoped credential mint"
                  description={
                    <>
                      Include <span className="font-mono text-pollen">mcp:call</span> for MCP hosts;{" "}
                      <span className="font-mono text-(--qs-magenta)">trading:live</span> unlocks real-money execution rails.
                    </>
                  }
                />

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <span className="v4-field-label">Label</span>
                    <input
                      value={keyLabel}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setKeyLabel(e.target.value)}
                      placeholder="prod-workstation"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-2">
                    <span className="v4-field-label">Scopes (comma-separated)</span>
                    <input
                      value={permissionsText}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setPermissionsText(e.target.value)}
                      placeholder="run, mcp:call"
                      className={cn(inputClass, "font-mono text-xs text-cyan")}
                    />
                  </div>
                </div>

                <button type="button" onClick={() => void handleMintKey()} disabled={mintBusy} className="qs-btn qs-btn--primary mt-4 disabled:opacity-50">
                  {mintBusy ? "Minting…" : "Generate qs_ep key"}
                </button>

                {mintedKey ? (
                  <div className="mt-4 rounded-xl border border-green-500/35 bg-green-500/10 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-green-300">Copy once</p>
                    <div className="mt-2 flex items-start gap-2">
                      <code className="flex-1 break-all font-mono text-[12px] leading-snug text-green-100">{mintedKey}</code>
                      <button
                        type="button"
                        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-green-200 hover:bg-green-500/15"
                        onClick={() => void copyText(mintedKey)}
                        aria-label="Copy API key"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ) : null}
              </V4Card>

              {metricsFetchMode !== "idle" ? (
                <p className="font-[family-name:var(--font-space-grotesk)] text-xs text-cyan/90" aria-live="polite">
                  {metricsFetchMode === "initial" ? "Loading metrics…" : "Syncing metrics (25s poll)…"}
                </p>
              ) : null}

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
                <HexMetric title="Runs" value={metrics?.metrics.runs_total ?? "—"} accent="cyan" />
                <HexMetric title="Success rate" value={metrics ? `${(metrics.metrics.success_rate * 100).toFixed(1)}%` : "—"} accent="pollen" />
                <HexMetric title="Verified passes" value={metrics?.metrics.runs_success ?? "—"} accent="green" />
                <HexMetric
                  title="Cost (USD est.)"
                  value={metrics ? metrics.metrics.cost_usd_total.toFixed(4) : "—"}
                  accent="magenta"
                />
              </div>

              {metricsError ? (
                <div className="rounded-2xl border border-[#FF00AA]/35 bg-[#FF00AA]/10 px-4 py-3 text-sm text-[#ffc6ea]" role="status">
                  {metricsError}
                </div>
              ) : null}

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <ChartCard
                  title="Latency pulse"
                  subtitle="Recent guarded invocations (newest right)."
                  emptyLabel="No runs recorded yet."
                  hasData={lineData.length > 0}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={lineData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a1a3e" />
                      <XAxis dataKey="shortT" stroke="#5a5a7a" tick={{ fontSize: 10 }} />
                      <YAxis stroke="#5a5a7a" tick={{ fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{ background: "#0d0d2b", border: "1px solid #1a1a3e", borderRadius: 12 }}
                        labelStyle={{ color: "#FFB800" }}
                      />
                      <Line type="monotone" dataKey="latency_ms" stroke="#00FFFF" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard
                  title="Outcome mix"
                  subtitle="Pass vs blocked/error slice from recent window."
                  emptyLabel="Awaiting telemetry."
                  hasData={barData.some((b) => b.count > 0)}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a1a3e" />
                      <XAxis dataKey="name" stroke="#5a5a7a" tick={{ fontSize: 10 }} />
                      <YAxis stroke="#5a5a7a" tick={{ fontSize: 10 }} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ background: "#0d0d2b", border: "1px solid #1a1a3e", borderRadius: 12 }}
                        labelStyle={{ color: "#FFB800" }}
                      />
                      <Bar dataKey="count" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </V4PageCanvas>
  );
}

interface HexMetricProps {
  title: string;
  value: string | number;
  accent: "cyan" | "pollen" | "green" | "magenta";
}

function HexMetric({ title, value, accent }: HexMetricProps) {
  const glow =
    accent === "cyan"
      ? "shadow-[0_0_22px_rgb(0_255_255/0.22)]"
      : accent === "pollen"
        ? "shadow-[0_0_22px_rgb(255_184_0/0.28)]"
        : accent === "green"
          ? "shadow-[0_0_22px_rgb(0_255_136/0.22)]"
          : "shadow-[0_0_22px_rgb(255_0_170/0.22)]";
  const border =
    accent === "cyan"
      ? "border-[color:var(--qs-border-2)]"
      : accent === "pollen"
        ? "border-pollen/35"
        : accent === "green"
          ? "border-[#00FF88]/35"
          : "border-[#FF00AA]/35";

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border bg-[#050510]/95 px-4 py-4",
        border,
        glow,
      )}
      style={{ clipPath: "polygon(12px 0%, calc(100% - 12px) 0%, 100% 12px, 100% calc(100% - 12px), calc(100% - 12px) 100%, 12px 100%, 0% calc(100% - 12px), 0% 12px)" }}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-zinc-500">{title}</p>
      <p className="mt-2 font-[family-name:var(--font-space-grotesk)] text-2xl font-bold tracking-tight text-white">{value}</p>
    </div>
  );
}

interface ChartCardProps {
  title: string;
  subtitle: string;
  emptyLabel: string;
  hasData: boolean;
  children: ReactNode;
}

function ChartCard({ title, subtitle, emptyLabel, hasData, children }: ChartCardProps) {
  return (
    <V4Card tight>
      <V4CardHeader as="h3" title={title} description={subtitle} />
      <div className="mt-2 h-64">{hasData ? children : <EmptyChart label={emptyLabel} />}</div>
    </V4Card>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-zinc-500">
      {label}
    </div>
  );
}
