"use client";

/**
 * Operator workflows board — horizontal DAG cards with periodic refresh.
 *
 * Lists ``GET /api/proxy/workflows`` and hydrates ``GET /api/proxy/workflows/:id`` on expand.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

interface WorkflowStep {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  agent_name?: string;
  duration_seconds?: number;
}

interface Workflow {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  recipe_tag?: string;
  steps: WorkflowStep[];
  created_at: string;
  progress_pct?: number;
}

interface ApiWorkflowBrief {
  id: string;
  original_task_text: string;
  status: string;
  total_steps: number;
  completed_steps: number;
  matching_recipe_id?: string | null;
}

interface ApiWorkflowDetail extends ApiWorkflowBrief {
  steps?: ApiWorkflowStep[];
}

interface ApiWorkflowStep {
  id: string;
  description: string;
  agent_role: string;
  status: string;
}

const STATUS_COLORS = {
  pending: { text: "#FFB800", bg: "rgba(255,184,0,0.1)", border: "rgba(255,184,0,0.3)" },
  running: { text: "#00E5FF", bg: "rgba(0,229,255,0.1)", border: "rgba(0,229,255,0.3)" },
  completed: { text: "#00FF88", bg: "rgba(0,255,136,0.1)", border: "rgba(0,255,136,0.3)" },
  failed: { text: "#FF3366", bg: "rgba(255,51,102,0.1)", border: "rgba(255,51,102,0.3)" },
  skipped: { text: "#5a5a7a", bg: "rgba(90,90,122,0.1)", border: "rgba(90,90,122,0.3)" },
} as const;

type UiWfFilter = "all" | "running" | "completed" | "failed";

function mapWorkflowFilterStatus(raw: string): Workflow["status"] {
  const v = raw.toUpperCase();
  if (v === "COMPLETED") {
    return "completed";
  }
  if (v === "FAILED" || v === "CANCELLED") {
    return "failed";
  }
  if (v === "EXECUTING") {
    return "running";
  }
  return "pending";
}

function wfUiBucket(status: Workflow["status"]): Exclude<UiWfFilter, "all"> | "pending" {
  if (status === "completed") {
    return "completed";
  }
  if (status === "failed") {
    return "failed";
  }
  if (status === "running") {
    return "running";
  }
  /** pending + decompose states land in Running bucket for pills (active work queue). */
  return "running";
}

function mapStepStatus(raw: string): WorkflowStep["status"] {
  const u = raw.toUpperCase();
  if (u === "RUNNING") {
    return "running";
  }
  if (u === "COMPLETED") {
    return "completed";
  }
  if (u === "FAILED") {
    return "failed";
  }
  if (u === "SKIPPED") {
    return "skipped";
  }
  return "pending";
}

function briefToWorkflow(b: ApiWorkflowBrief): Workflow {
  const total = b.total_steps || 0;
  const done = b.completed_steps || 0;
  const progress = total > 0 ? Math.round((done / total) * 100) : 0;
  const tag = b.matching_recipe_id ? String(b.matching_recipe_id).slice(0, 8) : undefined;
  return {
    id: String(b.id),
    title: b.original_task_text,
    status: mapWorkflowFilterStatus(b.status),
    recipe_tag: tag,
    steps: [],
    created_at: "",
    progress_pct: progress,
  };
}

function mergeDetail(base: Workflow, detail: ApiWorkflowDetail): Workflow {
  const steps: WorkflowStep[] = (detail.steps ?? []).map((st) => ({
    id: String(st.id),
    name: st.description,
    status: mapStepStatus(st.status),
    agent_name: String(st.agent_role).replace(/_/g, " "),
  }));
  const total = detail.total_steps || steps.length;
  const done = detail.completed_steps;
  const progress = total > 0 ? Math.round((done / total) * 100) : base.progress_pct ?? 0;
  return {
    ...base,
    status: mapWorkflowFilterStatus(detail.status),
    steps,
    progress_pct: progress,
  };
}

function StatusBadge({ status }: { status: keyof typeof STATUS_COLORS }): JSX.Element {
  const c = STATUS_COLORS[status];
  return (
    <span
      style={{
        fontSize: 10,
        fontFamily: "var(--font-hive-mono)",
        fontWeight: 700,
        padding: "2px 8px",
        borderRadius: 999,
        color: c.text,
        background: c.bg,
        border: `1px solid ${c.border}`,
      }}
    >
      {status}
    </span>
  );
}

function StepNode({ step, index, total }: { step: WorkflowStep; index: number; total: number }): JSX.Element {
  const c = STATUS_COLORS[step.status] ?? STATUS_COLORS.pending;
  const isLast = index === total - 1;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, position: "relative" }}>
        <div
          style={{
            width: 52,
            height: 52,
            flexShrink: 0,
            clipPath: "polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)",
            background: step.status === "completed" ? c.bg : "#141424",
            border: `2px solid ${c.text}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: step.status === "running" ? `0 0 16px ${c.text}66` : "none",
          }}
        >
          {step.status === "completed" && <span style={{ fontSize: 16 }}>✓</span>}
          {step.status === "running" && (
            <span className="qs-pulse" style={{ fontSize: 14 }}>
              ⚡
            </span>
          )}
          {step.status === "pending" && <span style={{ fontSize: 14, color: "#5a5a7a" }}>○</span>}
          {step.status === "failed" && <span style={{ fontSize: 14 }}>✗</span>}
          {step.status === "skipped" && <span style={{ fontSize: 14, color: "#5a5a7a" }}>—</span>}
        </div>
        <div style={{ textAlign: "center", width: 80 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: c.text }}>{step.name}</div>
          {step.agent_name && (
            <div style={{ fontSize: 9, color: "#5a5a7a", fontFamily: "var(--font-hive-mono)", marginTop: 2 }}>
              {step.agent_name}
            </div>
          )}
        </div>
      </div>
      {!isLast && (
        <div
          style={{
            width: 40,
            height: 2,
            background: step.status === "completed" ? "#00FF88" : "#1e1e35",
            flexShrink: 0,
            marginTop: -24,
          }}
        />
      )}
    </div>
  );
}

function WorkflowCard({
  wf,
  loadDetail,
}: {
  wf: Workflow;
  loadDetail: (id: string) => Promise<void>;
}): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const [hydrating, setHydrating] = useState(false);

  const pct =
    wf.progress_pct ??
    (wf.steps.length > 0
      ? Math.round((wf.steps.filter((s) => s.status === "completed").length / wf.steps.length) * 100)
      : 0);

  const badgeStatus: keyof typeof STATUS_COLORS =
    wf.status === "completed"
      ? "completed"
      : wf.status === "failed"
        ? "failed"
        : wf.status === "running"
          ? "running"
          : "pending";

  const c = STATUS_COLORS[badgeStatus];
  const timeAgo = (d: string) => {
    if (!d) {
      return "recent";
    }
    const diff = Date.now() - new Date(d).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1) {
      return "just now";
    }
    if (m < 60) {
      return `${m}m ago`;
    }
    return `${Math.floor(m / 60)}h ago`;
  };

  const canControl = wf.status === "running" || wf.status === "pending";

  const runControl = async (path: "pause" | "cancel") => {
    try {
      await fetch(`/api/proxy/operator/workflows/${encodeURIComponent(wf.id)}/${path}`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      /* best-effort */
    }
  };

  const toggle = async () => {
    const next = !expanded;
    setExpanded(next);
    if (next && wf.steps.length === 0) {
      setHydrating(true);
      await loadDetail(wf.id);
      setHydrating(false);
    }
  };

  return (
    <div
      style={{
        background: "#0f0f1a",
        border: `1px solid ${expanded ? c.border : "#1e1e35"}`,
        borderRadius: 12,
        overflow: "hidden",
        marginBottom: 12,
        transition: "border-color 0.2s",
      }}
    >
      <button
        type="button"
        onClick={() => void toggle()}
        style={{
          padding: "14px 18px",
          display: "flex",
          width: "100%",
          alignItems: "center",
          gap: 14,
          cursor: "pointer",
          background: "transparent",
          border: "none",
          textAlign: "left",
        }}
      >
        <div style={{ width: 3, height: 36, borderRadius: 2, background: c.text, flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: "#e8e8f0" }}>{wf.title}</span>
            <span style={{ fontSize: 10, color: "#5a5a7a", fontFamily: "var(--font-hive-mono)" }}>#{wf.id.slice(-6)}</span>
            {wf.recipe_tag && (
              <span
                style={{
                  fontSize: 9,
                  padding: "1px 7px",
                  borderRadius: 999,
                  background: "rgba(255,184,0,0.1)",
                  color: "#FFB800",
                  border: "1px solid rgba(255,184,0,0.25)",
                  fontFamily: "var(--font-hive-mono)",
                }}
              >
                {wf.recipe_tag}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <StatusBadge status={badgeStatus} />
            <span style={{ fontSize: 11, color: "#5a5a7a" }}>
              {wf.steps.length > 0 ? `${wf.steps.length} steps · ` : ""}
              {timeAgo(wf.created_at)}
            </span>
            {hydrating ? <span style={{ fontSize: 10, color: "#00e5ff" }}>Loading DAG…</span> : null}
          </div>
        </div>

        <div style={{ width: 120, flexShrink: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: "#5a5a7a" }}>Progress</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: c.text, fontFamily: "var(--font-hive-mono)" }}>
              {pct}%
            </span>
          </div>
          <div style={{ height: 4, background: "#1e1e35", borderRadius: 2, overflow: "hidden" }}>
            <div
              style={{ width: `${pct}%`, height: "100%", background: c.text, borderRadius: 2, transition: "width 0.5s" }}
            />
          </div>
        </div>

        <span style={{ color: "#5a5a7a", fontSize: 14, padding: "4px 8px" }} aria-hidden>
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && (
        <div style={{ borderTop: "1px solid #1e1e35", padding: "20px 18px" }}>
          {wf.steps.length === 0 && !hydrating ? (
            <div style={{ color: "#5a5a7a", fontSize: 13 }}>No steps defined</div>
          ) : wf.steps.length > 0 ? (
            <>
              <div style={{ overflowX: "auto" }}>
                <div style={{ display: "flex", alignItems: "flex-start", paddingBottom: 8, minWidth: "max-content" }}>
                  {wf.steps.map((step, i) => (
                    <StepNode key={step.id} step={step} index={i} total={wf.steps.length} />
                  ))}
                </div>
              </div>
              {wf.steps.some((s) => s.status !== "pending") && (
                <div style={{ marginTop: 16 }}>
                  <div
                    style={{
                      fontSize: 10,
                      color: "#5a5a7a",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginBottom: 8,
                    }}
                  >
                    Step Details
                  </div>
                  {wf.steps.map((step) => {
                    const sc = STATUS_COLORS[step.status] ?? STATUS_COLORS.pending;
                    return (
                      <div
                        key={step.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          padding: "7px 0",
                          borderBottom: "1px solid #1a1a2e",
                        }}
                      >
                        <div style={{ width: 7, height: 7, borderRadius: "50%", background: sc.text, flexShrink: 0 }} />
                        <span style={{ fontSize: 12, color: "#ccc", flex: 1 }}>{step.name}</span>
                        {step.agent_name && (
                          <span style={{ fontSize: 10, color: "#5a5a7a", fontFamily: "var(--font-hive-mono)" }}>
                            {step.agent_name}
                          </span>
                        )}
                        {step.duration_seconds !== undefined && (
                          <span style={{ fontSize: 10, color: "#5a5a7a", fontFamily: "var(--font-hive-mono)" }}>
                            {step.duration_seconds}s
                          </span>
                        )}
                        <StatusBadge status={step.status} />
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <div style={{ color: "#5a5a7a", fontSize: 13 }}>Fetching steps…</div>
          )}

          {canControl ? (
            <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => void runControl("pause")}
                style={{
                  padding: "6px 14px",
                  borderRadius: 7,
                  border: "1px solid rgba(255,184,0,0.3)",
                  background: "transparent",
                  color: "#FFB800",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                ⏸ Pause
              </button>
              <button
                type="button"
                onClick={() => void runControl("cancel")}
                style={{
                  padding: "6px 14px",
                  borderRadius: 7,
                  border: "1px solid rgba(255,51,102,0.3)",
                  background: "transparent",
                  color: "#FF3366",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                ✕ Cancel
              </button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function WorkflowsDagPage(): JSX.Element {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<UiWfFilter>("all");

  const loadWorkflows = useCallback(async () => {
    try {
      const res = await fetch("/api/proxy/workflows?limit=20", { credentials: "include" });
      if (res.status === 404 || !res.ok) {
        setWorkflows([]);
        return;
      }
      const data: unknown = await res.json();
      const rawRows: ApiWorkflowBrief[] = Array.isArray(data)
        ? (data as ApiWorkflowBrief[])
        : ((data as { workflows?: ApiWorkflowBrief[] }).workflows ??
            (data as { items?: ApiWorkflowBrief[] }).items ??
            []);
      setWorkflows(rawRows.map(briefToWorkflow));
    } catch {
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const r = await fetch(`/api/proxy/workflows/${encodeURIComponent(id)}`, { credentials: "include" });
      if (!r.ok) {
        return;
      }
      const detail = (await r.json()) as ApiWorkflowDetail;
      setWorkflows((prev) => prev.map((w) => (w.id !== id ? w : mergeDetail(w, detail))));
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    void loadWorkflows();
    const interval = setInterval(() => void loadWorkflows(), 8000);
    return () => clearInterval(interval);
  }, [loadWorkflows]);

  const filtered =
    filter === "all"
      ? workflows
      : workflows.filter((w) => {
          const b = wfUiBucket(w.status);
          return b === filter;
        });

  const counts = {
    all: workflows.length,
    running: workflows.filter((w) => wfUiBucket(w.status) === "running").length,
    completed: workflows.filter((w) => wfUiBucket(w.status) === "completed").length,
    failed: workflows.filter((w) => wfUiBucket(w.status) === "failed").length,
  };

  return (
    <div className="space-y-6">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#e8e8f0]">Workflows</h1>
          <p className="mt-1 text-[13px] text-[#5a5a7a]">DAG executions · auto-decomposed from tasks</p>
        </div>
        <Link href="/tasks/new" className="qs-btn qs-btn--primary">
          + New task
        </Link>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        {(["all", "running", "completed", "failed"] as const).map((f) => {
          const active = filter === f;
          const activeClass =
            f === "all"
              ? "qs-pill--active-amber"
              : f === "running"
                ? "qs-pill--active-cyan"
                : f === "completed"
                  ? "qs-pill--active-green"
                  : "qs-pill--active-red";
          return (
            <button key={f} type="button" onClick={() => setFilter(f)} className={cn("qs-pill capitalize", active && activeClass)}>
              {f} · {counts[f]}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "#5a5a7a" }}>Loading workflows…</div>
      ) : filtered.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: 60,
            background: "#0f0f1a",
            border: "1px solid #1e1e35",
            borderRadius: 14,
          }}
        >
          <div style={{ fontSize: 40, marginBottom: 12 }}>↗</div>
          <div style={{ color: "#e8e8f0", fontWeight: 600, marginBottom: 6 }}>
            {filter === "all" ? "No workflows yet" : `No ${filter} workflows`}
          </div>
          <div style={{ color: "#5a5a7a", fontSize: 13, marginBottom: 16 }}>
            Create a task and the Auto-Workflow Breaker will decompose it into steps
          </div>
          <Link href="/tasks/new" className="qs-btn qs-btn--primary">
            Create first task →
          </Link>
        </div>
      ) : (
        filtered.map((wf) => <WorkflowCard key={wf.id} wf={wf} loadDetail={loadDetail} />)
      )}
    </div>
  );
}
