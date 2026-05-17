"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { AgentSuggestionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface AgentSuggestionsPanelProps {
  className?: string;
}

function niceType(value: string): string {
  return value.replace(/_/g, " ");
}

export function AgentSuggestionsPanel({ className }: AgentSuggestionsPanelProps) {
  const [rows, setRows] = useState<AgentSuggestionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/proxy/agents/suggestions?limit=80", { cache: "no-store" });
      const body = (await res.json().catch(() => [])) as AgentSuggestionRow[] | { detail?: string };
      if (!res.ok) {
        throw new Error(Array.isArray(body) ? "Unable to load suggestions" : String(body.detail ?? "Unable to load suggestions"));
      }
      setRows(Array.isArray(body) ? body : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load suggestions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const pendingCount = useMemo(() => rows.filter((item) => item.status === "pending").length, [rows]);

  async function review(id: string, decision: "approve" | "reject"): Promise<void> {
    setBusyId(id);
    setError(null);
    try {
      const res = await fetch(`/api/proxy/agents/suggestions/${id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      const body = (await res.json().catch(() => ({}))) as AgentSuggestionRow | { detail?: string };
      if (!res.ok) {
        throw new Error("detail" in body ? String(body.detail) : "Review failed");
      }
      setRows((prev) => prev.map((row) => (row.id === id ? (body as AgentSuggestionRow) : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section id="agent-suggestions" className={cn("rounded-2xl border border-cyan/20 bg-hive-card/70 p-5", className)}>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Agent Suggestions</h2>
          <p className="mt-1 text-sm text-zinc-400">
            Self-proposed improvements from reflection cycles. Pending: <span className="text-amber-300">{pendingCount}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg border border-cyan/30 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-cyan-200 hover:border-cyan/50 hover:text-cyan-100"
        >
          Refresh
        </button>
      </header>

      {loading ? <p className="mt-4 text-sm text-zinc-500">Loading initiative suggestions…</p> : null}
      {!loading && rows.length === 0 ? (
        <div className="mt-4 rounded-xl border border-cyan/10 bg-hive-void/40 p-4 text-sm text-zinc-500">
          No suggestions yet. Agents will start proposing improvements after reflection cycles complete.
        </div>
      ) : null}

      {!loading ? (
        <div className="mt-4 space-y-3">
          {rows.map((row) => (
            <article key={row.id} className="rounded-xl border border-cyan/10 bg-hive-void/50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-zinc-100">{row.title}</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {niceType(row.proposal_type)} · role {row.proposed_by_role} · impact {(row.impact_score * 100).toFixed(0)}%
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide",
                    row.status === "approved"
                      ? "bg-emerald-500/20 text-emerald-300"
                      : row.status === "rejected"
                        ? "bg-rose-500/20 text-rose-300"
                        : "bg-amber-500/20 text-amber-300",
                  )}
                >
                  {row.status}
                </span>
              </div>
              <p className="mt-2 text-sm text-zinc-300">{row.description}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-500">
                <span>risk: {row.risk_level}</span>
                <span>manual approval: {row.requires_manual_approval ? "yes" : "no"}</span>
                {row.evaluation_reason ? <span>reason: {row.evaluation_reason}</span> : null}
              </div>
              {row.status === "pending" ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyId === row.id}
                    className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-50"
                    onClick={() => void review(row.id, "approve")}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busyId === row.id}
                    className="rounded-lg bg-rose-500/20 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/30 disabled:opacity-50"
                    onClick={() => void review(row.id, "reject")}
                  >
                    Reject
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
    </section>
  );
}
