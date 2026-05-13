"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import type { AgentRow, TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type DetailTab = "overview" | "config" | "tasks";

interface AgentConfigDto {
  system_prompt?: string;
  user_prompt_template?: string | null;
  output_format?: string;
  schedule_value?: string | null;
  schedule_type?: string | null;
  last_run_result?: Record<string, unknown> | string | null;
  last_run_at?: string | null;
  run_count?: number;
  tools?: unknown[];
  output_destination?: string;
  output_config?: Record<string, unknown>;
  is_active?: boolean;
}

const SWARM_COLORS: Record<string, string> = {
  scout: "#00E5FF",
  eval: "#FFB800",
  simulation: "#FF00AA",
  sim: "#FF00AA",
  action: "#00FF88",
};

function swarmKeyFromAgent(agent: AgentRow | null): string {
  if (!agent) return "scout";
  const blob = `${agent.swarm_purpose ?? ""} ${agent.hive_tier ?? ""}`.toLowerCase();
  if (blob.includes("eval")) return "eval";
  if (blob.includes("sim")) return "sim";
  if (blob.includes("action")) return "action";
  if (blob.includes("scout")) return "scout";
  return "scout";
}

export default function AgentDetailPage(): JSX.Element {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const idRaw = params?.id;
  const id = typeof idRaw === "string" ? idRaw : Array.isArray(idRaw) ? idRaw[0] : "";

  const [agent, setAgent] = useState<AgentRow | null>(null);
  const [config, setConfig] = useState<AgentConfigDto | null>(null);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<DetailTab>("overview");
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const loadAgent = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setLoadErr(null);
    try {
      const [ag, cf, tk] = await Promise.all([
        hiveGet<AgentRow>(`agents/${encodeURIComponent(id)}`),
        hiveGet<AgentConfigDto>(`agents/${encodeURIComponent(id)}/config`).catch(() => null),
        hiveGet<TaskRow[] | { tasks?: TaskRow[] } | { items?: TaskRow[] }>(
          `tasks?agent_id=${encodeURIComponent(id)}&limit=20`,
        ).catch(() => []),
      ]);
      setAgent(ag);
      setConfig(cf ?? null);
      let list: TaskRow[] = [];
      if (Array.isArray(tk)) {
        list = tk;
      } else if (tk && typeof tk === "object") {
        const bag = tk as { tasks?: TaskRow[]; items?: TaskRow[] };
        list = bag.tasks ?? bag.items ?? [];
      }
      setTasks(list);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Load failed";
      setLoadErr(msg);
      setAgent(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadAgent();
  }, [loadAgent]);

  async function runNow(): Promise<void> {
    if (!id) return;
    setRunning(true);
    try {
      const d = await hivePostJson<{ task_id?: string }>(`agents/${encodeURIComponent(id)}/run`, {});
      if (d?.task_id) {
        router.push("/tasks");
      }
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Run failed");
    } finally {
      setRunning(false);
    }
  }

  async function saveConfig(): Promise<void> {
    if (!config || !id) return;
    setSaving(true);
    try {
      const body = {
        system_prompt: config.system_prompt,
        user_prompt_template: config.user_prompt_template,
        output_format: config.output_format,
        schedule_value: config.schedule_value ?? undefined,
        schedule_type: config.schedule_type ?? undefined,
      };
      await hivePutJson<AgentConfigDto>(`agents/${encodeURIComponent(id)}/config`, body);
      await loadAgent();
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function togglePause(): Promise<void> {
    if (!id || !agent) return;
    const paused = agent.status.toLowerCase() === "paused";
    const path = paused ? "resume" : "pause";
    try {
      await hivePostJson(`agents/${encodeURIComponent(id)}/${path}`, {});
      await loadAgent();
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Pause/resume failed");
    }
  }

  if (!id) {
    return (
      <p className="p-10 text-center font-mono text-sm text-[var(--qs-red)]">Invalid agent id</p>
    );
  }

  if (loading) {
    return <p className="p-10 text-center font-mono text-sm text-[var(--qs-text-3)]">Loading agent…</p>;
  }

  if (loadErr || !agent) {
    return (
      <div className="p-10 text-center font-mono text-sm text-[var(--qs-red)]">
        {loadErr ?? "Agent not found"}
      </div>
    );
  }

  const swarmKey = swarmKeyFromAgent(agent);
  const color = SWARM_COLORS[swarmKey] ?? "#FFB800";
  const statusLower = agent.status.toLowerCase();
  const statusColor =
    statusLower === "running" ? "#00E5FF" : statusLower === "paused" ? "#FF3366" : "#00FF88";
  const idleish = statusLower === "idle" || statusLower === "offline";

  return (
    <div className="space-y-6 pb-10">
      <button
        type="button"
        onClick={() => router.back()}
        className="qs-btn qs-btn--ghost qs-btn--sm mb-2 self-start"
      >
        ← Back
      </button>

      <header className="flex flex-wrap items-start gap-5 lg:gap-8">
        <div
          className="relative flex h-[92px] w-20 shrink-0 items-center justify-center text-3xl"
          style={{
            clipPath: "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)",
            background: "var(--qs-surface-2)",
            outline: `2px solid ${color}50`,
            outlineOffset: -2,
            boxShadow: idleish ? "none" : `0 0 24px ${color}30`,
          }}
        >
          🐝
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <h1 className="font-[family-name:var(--font-poppins)] text-[22px] font-bold text-[var(--qs-text)]">
              {agent.name}
            </h1>
            <span
              className="rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-bold"
              style={{ borderColor: `${color}40`, background: `${color}18`, color }}
            >
              {swarmKey.toUpperCase()}
            </span>
            <span
              className="rounded-full border px-2.5 py-0.5 font-mono text-[10px]"
              style={{ borderColor: `${statusColor}35`, background: `${statusColor}12`, color: statusColor }}
            >
              {agent.status}
            </span>
          </div>
          <p className="mb-3 text-[13px] text-[var(--qs-text-3)]">
            {agent.role.replaceAll("_", " ")} · ◈ {(agent.pollen_points ?? 0).toLocaleString()} pollen
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={running}
              onClick={() => void runNow()}
              className="qs-btn qs-btn--primary disabled:opacity-40"
            >
              {running ? "Running…" : "▶ Run now"}
            </button>
            <button type="button" onClick={() => void togglePause()} className="qs-btn qs-btn--ghost qs-btn--sm">
              {statusLower === "paused" ? "▶ Resume" : "⏸ Pause"}
            </button>
            <button
              type="button"
              onClick={() => router.push(`/agents/${encodeURIComponent(id)}/edit`)}
              className="qs-btn qs-btn--cyan qs-btn--sm"
            >
              Full editor →
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          {[
            { label: "Tasks run", value: config?.run_count ?? "—" },
            {
              label: "Last run",
              value: config?.last_run_at ? new Date(String(config.last_run_at)).toLocaleDateString("sk-SK") : "Never",
            },
            { label: "Schedule", value: config?.schedule_value || "On demand" },
          ].map((s) => (
            <div
              key={s.label}
              className="min-w-[92px] rounded-[10px] border border-[var(--qs-border)] bg-[var(--qs-surface)] px-4 py-3 text-center"
            >
              <div className="mb-1 text-[11px] text-[var(--qs-text-3)]">{s.label}</div>
              <div className="font-mono text-sm font-semibold text-[var(--qs-text)]">{String(s.value)}</div>
            </div>
          ))}
        </div>
      </header>

      <div className="flex gap-1 border-b border-[var(--qs-border)]">
        {(["overview", "config", "tasks"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "border-b-2 px-4 py-2 font-[family-name:var(--font-poppins)] text-[13px] transition-colors",
              tab === t ? "border-[var(--qs-amber)] font-semibold text-[var(--qs-amber)]" : "border-transparent text-[var(--qs-text-3)]",
            )}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="qs-card rounded-[var(--qs-radius)]">
            <p className="qs-label mb-3">System prompt</p>
            <pre className="font-mono text-xs leading-relaxed text-[var(--qs-text-2)] whitespace-pre-wrap">
              {config?.system_prompt || "No system prompt configured"}
            </pre>
          </div>
          <div className="qs-card rounded-[var(--qs-radius)]">
            <p className="qs-label mb-3">Last result</p>
            <pre className="max-h-[220px] overflow-auto font-mono text-xs leading-relaxed text-[var(--qs-text-2)] whitespace-pre-wrap">
              {config?.last_run_result
                ? typeof config.last_run_result === "string"
                  ? config.last_run_result.slice(0, 800)
                  : JSON.stringify(config.last_run_result, null, 2).slice(0, 800)
                : "No runs yet"}
            </pre>
          </div>
        </div>
      )}

      {tab === "config" &&
        (config ? (
          <div className="qs-card rounded-[var(--qs-radius)]">
            <div className="mb-5 flex items-center justify-between gap-4">
              <span className="font-[family-name:var(--font-poppins)] text-[15px] font-semibold text-[var(--qs-text)]">
                Agent configuration
              </span>
              <button
                type="button"
                disabled={saving}
                onClick={() => void saveConfig()}
                className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40"
              >
                {saving ? "Saving…" : "💾 Save"}
              </button>
            </div>

            <div className="mb-4">
              <label className="qs-label">System prompt</label>
              <textarea
                className="qs-input min-h-[120px] resize-y"
                value={config.system_prompt ?? ""}
                rows={5}
                onChange={(e) =>
                  setConfig((c) => (c ? { ...c, system_prompt: e.target.value } : c))
                }
              />
            </div>

            <div className="mb-4">
              <label className="qs-label">User prompt template</label>
              <textarea
                className="qs-input min-h-[80px] resize-y"
                value={config.user_prompt_template ?? ""}
                rows={3}
                onChange={(e) =>
                  setConfig((c) => (c ? { ...c, user_prompt_template: e.target.value || null } : c))
                }
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="qs-label">Output format</label>
                <select
                  className="qs-input cursor-pointer"
                  value={config.output_format || "text"}
                  onChange={(e) =>
                    setConfig((c) => (c ? { ...c, output_format: e.target.value } : c))
                  }
                >
                  {["text", "markdown", "json", "excel", "csv", "html"].map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="qs-label">Schedule value</label>
                <input
                  className="qs-input"
                  value={config.schedule_value ?? ""}
                  placeholder="every 4 hours / daily 08:00"
                  onChange={(e) =>
                    setConfig((c) => (c ? { ...c, schedule_value: e.target.value || null } : c))
                  }
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="qs-card rounded-[var(--qs-radius)] text-[var(--qs-text-3)]">
            No saved config row — create or open the{" "}
            <button type="button" className="text-[var(--qs-cyan)] underline" onClick={() => router.push(`/agents/${id}/edit`)}>
              full editor
            </button>
            .
          </div>
        ))}

      {tab === "tasks" && (
        <div className="qs-card rounded-[var(--qs-radius)]">
          <p className="mb-4 font-[family-name:var(--font-poppins)] text-[15px] font-semibold text-[var(--qs-text)]">
            Task history
          </p>
          {tasks.length === 0 ? (
            <p className="py-12 text-center text-[var(--qs-text-3)]">No tasks yet — try Run now</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {tasks.map((task: TaskRow) => {
                const st = (task.status ?? "").toLowerCase();
                const sc: Record<string, string> = {
                  completed: "#00FF88",
                  failed: "#FF3366",
                  running: "#00E5FF",
                  queued: "#FFB800",
                  pending: "#FFB800",
                };
                const tc = sc[st] ?? "#5a5a7a";
                return (
                  <li
                    key={task.id}
                    className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--qs-border)] bg-[var(--qs-surface-2)] px-3 py-3"
                  >
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: tc }} />
                    <span className="min-w-0 flex-1 text-[13px] text-[#cccce0]">{task.title || "Untitled"}</span>
                    <span
                      className="rounded-full border px-2 py-0.5 font-mono text-[10px]"
                      style={{
                        borderColor: `${tc}40`,
                        color: tc,
                        background: `${tc}14`,
                      }}
                    >
                      {task.status}
                    </span>
                    <span className="font-mono text-[11px] text-[var(--qs-text-3)]">
                      {task.created_at ? new Date(task.created_at).toLocaleString("sk-SK") : ""}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
