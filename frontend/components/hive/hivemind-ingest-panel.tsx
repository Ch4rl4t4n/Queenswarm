"use client";

import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  Loader2,
  Moon,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Tag,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  V4Badge,
  V4BarRow,
  V4Card,
  V4CardHeader,
  V4Chip,
  V4IconKnowledge,
  V4Stat,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface VaultSample {
  doc_id: string;
  title: string;
  tags: string[];
  updated_at: string;
}

interface TagHit {
  tag: string;
  hits: number;
}

interface IngestOverview {
  window_hours: number;
  as_of: string;
  headline: {
    vault_documents_last_window: number;
    hivemind_candidate_pages: number;
    contract_compliance_pct: number | null;
    dump_pending: number;
    dream_insights_last_window: number;
    quality_signal: "green" | "amber" | "red";
  };
  vault_documents: {
    total_last_window: number;
    with_hivemind_tag: number;
    tags_top: TagHit[];
    samples: VaultSample[];
  };
  dump_sleep: {
    by_status: Record<string, number>;
    pending_count: number;
    oldest_pending_at: string | null;
  };
  dream_insights: {
    count_last_window: number;
    latest_at: string | null;
  };
  notes: string[];
}

interface CrossCheckSample {
  swarm_name: string;
  at: string;
  severity: string;
  message: string;
}

interface CrossCheckOverview {
  window_hours: number;
  headline: {
    grok_calls_window: number;
    grok_spend_usd: number;
    verdict_false_signals_window: number;
    session_cost_cap_usd: number;
  };
  signals: {
    total: number;
    by_severity: Record<string, number>;
    samples: CrossCheckSample[];
  };
  notes: string[];
}

const SIGNAL_BADGE: Record<
  IngestOverview["headline"]["quality_signal"],
  { tone: "ok" | "warn" | "err"; label: string }
> = {
  green: { tone: "ok", label: "Contract healthy" },
  amber: { tone: "warn", label: "Warming up" },
  red: { tone: "err", label: "No ingest yet" },
};

const FLOW_STEPS = [
  { key: "agents", label: "Agents", color: "var(--qs-magenta)" },
  { key: "notion", label: "[INSIGHT] page", color: "var(--qs-pollen, #ffb800)" },
  { key: "graphify", label: "Auto-Graphify", color: "var(--qs-cyan)" },
  { key: "vault", label: "VaultDocument", color: "var(--qs-green)" },
] as const;

function formatPct(value: number | null): string {
  if (value == null) return "—";
  return `${value.toFixed(0)}%`;
}

function formatAge(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const minutes = Math.max(0, Math.floor((Date.now() - then) / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function complianceBarTone(pct: number | null): "ok" | "warn" | "err" {
  if (pct == null || pct === 0) return "err";
  if (pct >= 80) return "ok";
  if (pct >= 50) return "warn";
  return "err";
}

/** Operator panel — HiveMind Quality Contract growth + Grok cross-check observability. */
export function HiveMindIngestPanel({
  windowHours = 24,
  crossCheckWindowHours = 168,
}: {
  readonly windowHours?: number;
  readonly crossCheckWindowHours?: number;
}): JSX.Element {
  const [data, setData] = useState<IngestOverview | null>(null);
  const [cc, setCc] = useState<CrossCheckOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [body, ccBody] = await Promise.all([
        hiveGet<IngestOverview>(`hive-mind/insights/overview?window_hours=${windowHours}`),
        hiveGet<CrossCheckOverview>(
          `hive-mind/insights/cross-check?window_hours=${crossCheckWindowHours}`,
        ),
      ]);
      setData(body);
      setCc(ccBody);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Ingest overview unavailable.");
    } finally {
      setLoading(false);
    }
  }, [windowHours, crossCheckWindowHours]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(id);
  }, [load]);

  const signal = data?.headline.quality_signal ?? "amber";
  const signalMeta = SIGNAL_BADGE[signal];
  const compliancePct = data?.headline.contract_compliance_pct ?? null;
  const tagged = data?.headline.hivemind_candidate_pages ?? 0;
  const vaultTotal = data?.headline.vault_documents_last_window ?? 0;
  const taggedRatio =
    vaultTotal > 0 ? Math.round((tagged / vaultTotal) * 100) : 0;

  return (
    <V4Card
      glow
      tight
      className={cn(
        "relative overflow-hidden border-(--qs-magenta)/35",
        "bg-[linear-gradient(135deg,rgba(232,121,249,0.08)_0%,rgba(7,3,15,0.92)_42%,rgba(111,214,255,0.06)_100%)]",
      )}
      aria-label="HiveMind ingest dashboard"
    >
      {/* ambient glow orbs */}
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-30 blur-3xl"
        style={{ background: "radial-gradient(circle, var(--qs-magenta) 0%, transparent 70%)" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -bottom-12 -left-12 h-32 w-32 rounded-full opacity-20 blur-3xl"
        style={{ background: "radial-gradient(circle, var(--qs-cyan) 0%, transparent 70%)" }}
        aria-hidden
      />

      <div className="relative z-1">
        <V4CardHeader
          kicker="HiveMind"
          title="Quality Contract · ingest dashboard"
          description="Tracks whether agents feed verified [INSIGHT] pages into Auto-Graphify and Neo4j — the closed loop for swarm memory."
          as="h3"
          actions={
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={loading}
              onClick={() => void load()}
            >
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} aria-hidden />
              Refresh
            </button>
          }
        />

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="v4-status-pill inline-flex">
            <span className="hive-pulse-dot" aria-hidden />
            Live · {windowHours}h window
          </span>
          <V4Badge tone={signalMeta.tone}>{signalMeta.label}</V4Badge>
          {data ? (
            <>
              <V4Badge tone="purple">{vaultTotal} VaultDocs</V4Badge>
              <V4Badge tone={tagged > 0 ? "gold" : "warn"}>
                {tagged} hivemind-candidate
              </V4Badge>
            </>
          ) : null}
        </div>

        {error ? (
          <p className="mt-4 rounded-(--qs-radius-sm) border border-(--qs-red)/40 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">
            {error}
          </p>
        ) : null}

        {loading && !data ? (
          <div className="v4-stat-grid mt-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="v4-stat h-[120px] animate-pulse bg-white/5" />
            ))}
          </div>
        ) : null}

        {data ? (
          <>
            <div className="v4-stat-grid mt-4">
              <V4Stat
                label="VaultDocuments"
                value={data.headline.vault_documents_last_window}
                icon={Database}
                iconTone="purple"
                foot="Auto-Graphify ingest"
              />
              <V4Stat
                label="Contract compliance"
                value={formatPct(compliancePct)}
                icon={ShieldCheck}
                iconTone={complianceBarTone(compliancePct) === "ok" ? "green" : "cyan"}
                foot="% tagged hivemind-candidate"
                valueVariant={complianceBarTone(compliancePct) === "ok" ? "gold" : "text"}
              />
              <V4Stat
                label="Dream insights"
                value={data.headline.dream_insights_last_window}
                icon={Moon}
                iconTone="purple"
                foot={
                  data.dream_insights.latest_at
                    ? `latest ${formatAge(data.dream_insights.latest_at)}`
                    : "overnight reasoning"
                }
              />
              <V4Stat
                label="Dump queue"
                value={data.headline.dump_pending}
                icon={Clock}
                iconTone={data.headline.dump_pending > 5 ? "default" : "green"}
                foot={
                  data.dump_sleep.oldest_pending_at
                    ? `oldest ${formatAge(data.dump_sleep.oldest_pending_at)}`
                    : "queue clean"
                }
              />
            </div>

            {/* ingest pipeline — visual explainer */}
            <div className="v4-embedding-head-card mt-4 border-(--qs-pollen)/20 bg-black/20">
              <p className="v4-label-kicker mb-3">Ingest pipeline</p>
              <div className="flex flex-wrap items-center gap-1 sm:gap-2">
                {FLOW_STEPS.map((step, idx) => (
                  <div key={step.key} className="flex items-center gap-1 sm:gap-2">
                    <span
                      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide"
                      style={{
                        borderColor: `${step.color}55`,
                        color: step.color,
                        boxShadow: `0 0 12px ${step.color}22`,
                      }}
                    >
                      <span
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: step.color }}
                        aria-hidden
                      />
                      {step.label}
                    </span>
                    {idx < FLOW_STEPS.length - 1 ? (
                      <span className="text-[10px] text-(--qs-text-3)" aria-hidden>
                        →
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
              <div className="mt-4 space-y-3">
                <V4BarRow
                  label="Compliance"
                  value={formatPct(compliancePct)}
                  pct={compliancePct ?? 0}
                />
                <V4BarRow
                  label="Tagged docs"
                  value={`${tagged} / ${vaultTotal}`}
                  pct={taggedRatio}
                />
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="v4-embedding-head-card border-(--qs-cyan)/20">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Tag className="h-4 w-4 text-(--qs-cyan)" aria-hidden />
                    <span className="v4-label-kicker">Top tags</span>
                  </div>
                  <V4Badge tone="info">{data.vault_documents.tags_top.length}</V4Badge>
                </div>
                {data.vault_documents.tags_top.length === 0 ? (
                  <p className="text-xs text-(--qs-text-3)">
                    No tagged VaultDocuments yet — run a swarm routine or approve a sub-agent.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {data.vault_documents.tags_top.map((t) => (
                      <V4Chip
                        key={t.tag}
                        type="span"
                        count={t.hits}
                        className={cn(
                          t.tag === "hivemind-candidate" &&
                            "border-(--qs-pollen)/50 text-(--qs-pollen) shadow-[0_0_14px_rgba(255,184,0,0.15)]",
                        )}
                      >
                        #{t.tag}
                      </V4Chip>
                    ))}
                  </div>
                )}
              </div>

              <div className="v4-embedding-head-card border-(--qs-green)/20">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-(--qs-green)" aria-hidden />
                    <span className="v4-label-kicker">Recent VaultDocs</span>
                  </div>
                  <V4Badge tone="ok">{data.vault_documents.samples.length}</V4Badge>
                </div>
                {data.vault_documents.samples.length === 0 ? (
                  <p className="text-xs text-(--qs-text-3)">
                    No recent ingest — Auto-Graphify idle or vault empty.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {data.vault_documents.samples.map((s) => (
                      <li
                        key={s.doc_id}
                        className="flex items-center gap-3 rounded-(--qs-radius-sm) border border-(--qs-border)/60 bg-black/25 px-3 py-2 transition-colors hover:border-(--qs-pollen)/25"
                      >
                        <Brain className="h-3.5 w-3.5 shrink-0 text-(--qs-magenta)" aria-hidden />
                        <span className="min-w-0 flex-1 truncate text-xs text-(--qs-text)" title={s.title}>
                          {s.title}
                        </span>
                        <span className="shrink-0 font-mono text-[10px] text-(--qs-text-3)">
                          {formatAge(s.updated_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {data.notes.length > 0 ? (
              <ul className="mt-4 space-y-2">
                {data.notes.map((note, idx) => (
                  <li
                    key={idx}
                    className={cn(
                      "flex items-start gap-2.5 rounded-(--qs-radius-lg) border px-3 py-2.5 text-[11px] leading-relaxed",
                      signal === "green"
                        ? "border-(--qs-green)/30 bg-(--qs-green)/5 text-(--qs-text-2)"
                        : "border-(--qs-amber)/35 bg-(--qs-amber)/5 text-(--qs-text-2)",
                    )}
                  >
                    {signal === "green" ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-(--qs-green)" aria-hidden />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-(--qs-amber)" aria-hidden />
                    )}
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}

        {cc ? (
          <V4Card
            tight
            className="relative mt-5 overflow-hidden border-(--qs-cyan)/35 bg-[linear-gradient(135deg,rgba(111,214,255,0.07)_0%,rgba(7,3,15,0.85)_100%)] p-0 shadow-none"
          >
            <div className="p-4 sm:p-5">
              <V4CardHeader
                kicker="Truth arbiter"
                title="Grok cross-check protocol"
                description={`When confidence < high, agents ask xai/grok-3-mini before writing to HiveMind. Window: ${cc.window_hours}h.`}
                as="h3"
              />

              <div className="mt-3 flex flex-wrap gap-2">
                <V4Badge tone="info">{cc.headline.grok_calls_window} Grok calls</V4Badge>
                <V4Badge tone="gold">${cc.headline.grok_spend_usd.toFixed(3)} spend</V4Badge>
                <V4Badge tone={cc.signals.total > 0 ? "warn" : "ok"}>
                  {cc.signals.total} verdict=false
                </V4Badge>
                <V4Badge tone="purple">cap ${cc.headline.session_cost_cap_usd.toFixed(2)}</V4Badge>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <V4Stat
                  label="Grok calls"
                  value={cc.headline.grok_calls_window}
                  icon={Zap}
                  iconTone="cyan"
                  foot="xai/grok-3-mini"
                />
                <V4Stat
                  label="Spend"
                  value={`$${cc.headline.grok_spend_usd.toFixed(3)}`}
                  icon={Sparkles}
                  iconTone="cyan"
                  valueVariant="text"
                />
                <V4Stat
                  label="Rejected"
                  value={cc.signals.total}
                  icon={ShieldCheck}
                  iconTone={cc.signals.total > 5 ? "default" : "green"}
                  foot="verdict=false notes"
                />
                <V4Stat
                  label="Session cap"
                  value={`$${cc.headline.session_cost_cap_usd.toFixed(2)}`}
                  icon={V4IconKnowledge}
                  iconTone="purple"
                  valueVariant="text"
                />
              </div>

              {cc.signals.samples.length > 0 ? (
                <ul className="mt-4 space-y-2">
                  {cc.signals.samples.slice(0, 4).map((sample, idx) => (
                    <li
                      key={`${sample.at}-${idx}`}
                      className="flex flex-wrap items-start gap-2 rounded-(--qs-radius-sm) border border-(--qs-border)/50 bg-black/30 px-3 py-2 text-[11px]"
                    >
                      <V4Badge tone={sample.severity === "error" ? "err" : "warn"}>
                        {sample.severity}
                      </V4Badge>
                      <span className="font-mono text-[10px] text-(--qs-text-3)">
                        {formatAge(sample.at)}
                      </span>
                      <span className="font-medium text-(--qs-cyan)">{sample.swarm_name}</span>
                      <span className="w-full text-(--qs-text-2)">{sample.message}</span>
                    </li>
                  ))}
                </ul>
              ) : null}

              {cc.notes.length > 0 ? (
                <ul className="mt-3 space-y-1 border-t border-(--qs-border)/40 pt-3">
                  {cc.notes.map((note, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-[11px] text-(--qs-text-3)">
                      <Sparkles className="mt-0.5 h-3 w-3 shrink-0 text-(--qs-cyan)" aria-hidden />
                      {note}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </V4Card>
        ) : null}
      </div>
    </V4Card>
  );
}
