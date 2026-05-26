"use client";

import {
  Activity,
  Code2,
  Cpu,
  GitCommit,
  Layers,
  Loader2,
  Monitor,
  RefreshCw,
  Timer,
} from "lucide-react";
import { useCallback, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4Chip,
  V4Stat,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import { cn } from "@/lib/utils";

const POLL_MS = 120_000;

interface StackSplitRow {
  name: string;
  lines: number;
  color: string;
}

interface LanguageRow {
  language: string;
  lines: number;
  pct: number;
}

interface WeeklyCommitRow {
  week: string;
  commits: number;
}

interface ArchLayer {
  id: string;
  label: string;
  description: string;
  path: string;
  lines: number;
  files: number;
  exists: boolean;
  color: string;
  order: number;
}

interface ArchSide {
  loc: { total_lines: number; total_files: number; available?: boolean };
  architecture: {
    kind: "frontend" | "backend";
    title: string;
    flow: string[];
    layers: ArchLayer[];
  };
}

interface CodebaseAtlasPayload {
  generated_at: string;
  repo_root: string;
  git_available: boolean;
  summary: {
    total_lines: number;
    frontend_lines: number;
    backend_lines: number;
    frontend_files: number;
    backend_files: number;
    estimated_dev_hours: number;
    commit_count: number;
    active_dev_days: number;
    coding_sessions: number;
    first_commit_at: string | null;
    last_commit_at: string | null;
  };
  stack_split: StackSplitRow[];
  languages: LanguageRow[];
  weekly_commits: WeeklyCommitRow[];
  frontend: ArchSide;
  backend: ArchSide;
}

type ArchTab = "frontend" | "backend";

function formatLines(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function formatHours(h: number): string {
  if (h >= 24) return `${(h / 24).toFixed(1)}d`;
  return `${h.toFixed(0)}h`;
}

function shortWeek(isoWeek: string): string {
  const parts = isoWeek.split("-W");
  return parts.length === 2 ? `W${parts[1]}` : isoWeek.slice(-3);
}

function AtlasTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; name: string; payload?: { color?: string } }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-(--qs-pollen)/40 bg-[#050510] px-3 py-2 text-xs shadow-[0_0_20px_rgb(255_184_0/0.15)]">
      {label ? <p className="mb-1 font-mono text-(--qs-text-3)">{label}</p> : null}
      {payload.map((row) => (
        <p key={row.name} className="text-(--qs-text)" style={{ color: row.payload?.color ?? undefined }}>
          {row.name}: <strong>{typeof row.value === "number" ? formatLines(row.value) : row.value}</strong>
        </p>
      ))}
    </div>
  );
}

function ArchitectureMap({ side }: { side: ArchSide }) {
  const maxLines = Math.max(...side.architecture.layers.map((l) => l.lines), 1);
  const total = side.architecture.layers.reduce((s, l) => s + l.lines, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-1.5">
        {side.architecture.flow.map((step, idx) => (
          <div key={step} className="flex items-center gap-1.5">
            <span className="rounded-full border border-(--qs-cyan)/30 bg-(--qs-cyan)/10 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-(--qs-cyan)">
              {step}
            </span>
            {idx < side.architecture.flow.length - 1 ? (
              <span className="text-(--qs-text-3)" aria-hidden>
                →
              </span>
            ) : null}
          </div>
        ))}
      </div>

      <div className="space-y-2">
        {side.architecture.layers.map((layer) => {
          const pct = total > 0 ? Math.round((layer.lines / total) * 100) : 0;
          const barPct = Math.max(4, (layer.lines / maxLines) * 100);
          return (
            <div
              key={layer.id}
              className={cn(
                "rounded-xl border bg-black/30 p-3 transition-colors",
                layer.exists ? "border-(--qs-border)/80 hover:border-(--qs-pollen)/25" : "border-(--qs-border)/40 opacity-50",
              )}
            >
              <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-(--qs-text)">{layer.label}</p>
                  <p className="text-[10px] text-(--qs-text-3)">{layer.description}</p>
                  <p className="mt-0.5 font-mono text-[9px] text-(--qs-text-3)">{layer.path}</p>
                </div>
                <div className="text-right">
                  <p className="font-(family-name:--qs-font-display) text-lg" style={{ color: layer.color }}>
                    {formatLines(layer.lines)}
                  </p>
                  <p className="text-[10px] text-(--qs-text-3)">
                    {layer.files} files · {pct}%
                  </p>
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${barPct}%`,
                    backgroundColor: layer.color,
                    boxShadow: `0 0 12px ${layer.color}66`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Command Center mini-section — LOC, dev hours, FE/BE architecture atlas. */
export function CommandCenterCodebaseAtlas({ enabled }: { enabled: boolean }) {
  const [data, setData] = useState<CodebaseAtlasPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [archTab, setArchTab] = useState<ArchTab>("frontend");

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    try {
      const body = await hiveGet<CodebaseAtlasPayload>("operator/command-center/codebase-atlas");
      setData(body);
      setError(null);
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Codebase atlas unavailable.");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useIntervalWhenVisible(() => void load(), enabled ? POLL_MS : null);

  if (!enabled) return null;

  const activeSide = archTab === "frontend" ? data?.frontend : data?.backend;

  return (
    <V4Card
      glow
      tight
      className={cn(
        "relative overflow-hidden border-(--qs-purple)/35 p-0",
        "bg-[linear-gradient(135deg,rgba(153,102,255,0.1)_0%,rgba(7,3,15,0.94)_45%,rgba(111,214,255,0.07)_100%)]",
      )}
    >
      <div
        className="pointer-events-none absolute -right-20 top-0 h-48 w-48 rounded-full opacity-25 blur-3xl"
        style={{ background: "radial-gradient(circle, #9966ff 0%, transparent 70%)" }}
        aria-hidden
      />

      <div className="relative z-1 border-b border-(--qs-border)/60 px-4 py-4 md:px-6">
        <V4CardHeader
          as="h3"
          kicker="Dev · codebase"
          title="Codebase Atlas"
          description="Riadky kódu, odhadované hodiny vývoja (git sessions) a mapa architektúry — prepni FE / BE."
          actions={
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" disabled={loading} onClick={() => void load()}>
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} aria-hidden />
              Refresh
            </button>
          }
        />
      </div>

      {error && !data ? (
        <p className="px-4 py-6 text-sm text-(--qs-red) md:px-6">{error}</p>
      ) : null}

      {loading && !data ? (
        <div className="flex min-h-[200px] items-center justify-center gap-2 px-4 py-8">
          <Loader2 className="h-6 w-6 animate-spin text-pollen" aria-hidden />
          <span className="text-sm text-(--qs-text-3)">Scanning repository…</span>
        </div>
      ) : null}

      {data ? (
        <div className="space-y-4 px-4 py-4 md:px-6 md:py-5">
          <div className="flex flex-wrap gap-2">
            <V4Badge tone="purple">{formatLines(data.summary.total_lines)} LOC total</V4Badge>
            <V4Badge tone="info">{formatLines(data.summary.frontend_lines)} FE</V4Badge>
            <V4Badge tone="gold">{formatLines(data.summary.backend_lines)} BE</V4Badge>
            {data.git_available ? (
              <V4Badge tone="ok">{data.summary.commit_count} commits</V4Badge>
            ) : (
              <V4Badge tone="warn">git n/a</V4Badge>
            )}
          </div>

          <div className="v4-stat-grid">
            <V4Stat
              label="Total lines"
              value={formatLines(data.summary.total_lines)}
              icon={Code2}
              iconTone="purple"
              foot={`${data.summary.frontend_files + data.summary.backend_files} source files`}
            />
            <V4Stat
              label="Dev hours (est.)"
              value={formatHours(data.summary.estimated_dev_hours)}
              icon={Timer}
              iconTone="cyan"
              foot={`${data.summary.coding_sessions} sessions · ${data.summary.active_dev_days} active days`}
            />
            <V4Stat
              label="Frontend"
              value={formatLines(data.summary.frontend_lines)}
              icon={Monitor}
              iconTone="cyan"
              foot="Next.js · TS/TSX"
            />
            <V4Stat
              label="Backend"
              value={formatLines(data.summary.backend_lines)}
              icon={Cpu}
              iconTone="purple"
              foot="FastAPI · Python"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {/* Stack pie */}
            <div className="rounded-xl border border-(--qs-border)/70 bg-black/35 p-4">
              <div className="mb-2 flex items-center gap-2">
                <Layers className="h-4 w-4 text-(--qs-magenta)" aria-hidden />
                <span className="v4-label-kicker">Stack split</span>
              </div>
              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.stack_split}
                      dataKey="lines"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={48}
                      outerRadius={72}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {data.stack_split.map((row) => (
                        <Cell key={row.name} fill={row.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<AtlasTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex flex-wrap justify-center gap-3">
                {data.stack_split.map((row) => (
                  <span key={row.name} className="flex items-center gap-1.5 text-[10px] text-(--qs-text-2)">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: row.color }} aria-hidden />
                    {row.name} · {formatLines(row.lines)}
                  </span>
                ))}
              </div>
            </div>

            {/* Languages bar */}
            <div className="rounded-xl border border-(--qs-border)/70 bg-black/35 p-4">
              <div className="mb-2 flex items-center gap-2">
                <Code2 className="h-4 w-4 text-(--qs-cyan)" aria-hidden />
                <span className="v4-label-kicker">Languages</span>
              </div>
              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.languages.slice(0, 8)} layout="vertical" margin={{ left: 4, right: 8 }}>
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="language"
                      width={72}
                      tick={{ fill: "#a1a1aa", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<AtlasTooltip />} />
                    <Bar dataKey="lines" radius={[0, 6, 6, 0]}>
                      {data.languages.slice(0, 8).map((_, idx) => (
                        <Cell
                          key={idx}
                          fill={["#6fd6ff", "#e879f9", "#ffb800", "#5be3b2", "#9966ff", "#ff00aa", "#71717a", "#a1a1aa"][idx % 8]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Weekly commits */}
          {data.weekly_commits.length > 1 ? (
            <div className="rounded-xl border border-(--qs-border)/70 bg-black/35 p-4">
              <div className="mb-2 flex items-center gap-2">
                <GitCommit className="h-4 w-4 text-(--qs-green)" aria-hidden />
                <span className="v4-label-kicker">Commit activity (12 weeks)</span>
                <V4Badge tone="info" className="ml-auto">
                  {data.summary.commit_count} total
                </V4Badge>
              </div>
              <div className="h-36 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.weekly_commits.map((w) => ({ ...w, label: shortWeek(w.week) }))}>
                    <defs>
                      <linearGradient id="atlasCommitGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#9966ff" stopOpacity={0.45} />
                        <stop offset="100%" stopColor="#9966ff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="label"
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      axisLine={{ stroke: "rgb(153 102 255 / 0.15)" }}
                      tickLine={false}
                    />
                    <YAxis
                      allowDecimals={false}
                      width={24}
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      axisLine={{ stroke: "rgb(153 102 255 / 0.15)" }}
                      tickLine={false}
                    />
                    <Tooltip content={<AtlasTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="commits"
                      name="Commits"
                      stroke="#9966ff"
                      strokeWidth={2}
                      fill="url(#atlasCommitGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {data.summary.first_commit_at ? (
                <p className="mt-2 font-mono text-[10px] text-(--qs-text-3)">
                  First commit {new Date(data.summary.first_commit_at).toLocaleDateString()} · last{" "}
                  {data.summary.last_commit_at
                    ? new Date(data.summary.last_commit_at).toLocaleDateString()
                    : "—"}
                </p>
              ) : null}
            </div>
          ) : null}

          {/* Architecture tabs */}
          <div className="rounded-xl border border-(--qs-pollen)/25 bg-black/25 p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-pollen" aria-hidden />
                <span className="text-sm font-semibold text-(--qs-text)">Architecture map</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <V4Chip active={archTab === "frontend"} onClick={() => setArchTab("frontend")} type="button">
                  Frontend
                </V4Chip>
                <V4Chip active={archTab === "backend"} onClick={() => setArchTab("backend")} type="button">
                  Backend
                </V4Chip>
              </div>
            </div>

            {activeSide ? (
              <>
                <p className="mb-3 text-xs text-(--qs-text-3)">
                  {activeSide.architecture.title} · {formatLines(activeSide.loc.total_lines ?? 0)} lines ·{" "}
                  {activeSide.loc.total_files ?? 0} files
                </p>
                <ArchitectureMap side={activeSide} />
              </>
            ) : null}
          </div>

          <p className="font-mono text-[10px] text-(--qs-text-3)">
            Repo: {data.repo_root} · generated {new Date(data.generated_at).toLocaleString()} · poll{" "}
            {POLL_MS / 1000}s
          </p>
        </div>
      ) : null}
    </V4Card>
  );
}
