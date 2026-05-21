"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import type { AgentSuggestionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface AgentSuggestionsPanelProps {
  className?: string;
}

function niceType(value: string): string {
  return value.replace(/_/g, " ");
}

function impactTone(score: number): "gold" | "info" {
  return score >= 0.7 ? "gold" : "info";
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
      const body = await hiveGet<AgentSuggestionRow[]>("agents/suggestions?limit=80");
      setRows(Array.isArray(body) ? body : []);
    } catch (err) {
      setError(err instanceof HiveApiError ? err.message : "Unable to load suggestions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, DASHBOARD_BOOT_STAGGER_MS.agentSuggestions);
    return () => window.clearTimeout(timer);
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
    <V4Card id="agent-suggestions" className={cn("v4-card-interactive scroll-mt-28", className)}>
      <V4CardHeader
        title="Agent suggestions"
        description="Self-proposed improvements from reflection cycles · approve to apply, reject to log."
        actions={
          <>
            <V4Badge tone="purple">{pendingCount} pending</V4Badge>
            <button type="button" onClick={() => void load()} className="qs-btn qs-btn--ghost qs-btn--sm">
              Refresh
            </button>
          </>
        }
      />

      {loading ? <p className="text-sm text-(--qs-text-3)">Loading initiative suggestions…</p> : null}
      {!loading && rows.length === 0 ? (
        <div className="v4-empty py-8 text-sm">No suggestions yet. Agents will start proposing after reflection cycles complete.</div>
      ) : null}

      {!loading ? (
        <div className="flex flex-col gap-3">
          {rows.map((row) => (
            <article key={row.id} className="v4-suggestion-row">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 flex-1 gap-3">
                  <V4Badge tone={impactTone(row.impact_score)}>
                    {row.impact_score >= 0.7 ? "high" : "med"} impact
                  </V4Badge>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-(--qs-text)">{row.title}</p>
                    <p className="mt-1 text-sm text-(--qs-text-2)">{row.description}</p>
                    <p className="mt-2 text-[11px] text-(--qs-text-3)">
                      proposed by <span className="text-pollen">{row.proposed_by_role}</span> · {niceType(row.proposal_type)}
                    </p>
                  </div>
                </div>
                <V4Badge tone={row.status === "approved" ? "ok" : row.status === "rejected" ? "err" : "warn"}>
                  {row.status}
                </V4Badge>
              </div>
              {row.status === "pending" ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" disabled={busyId === row.id} className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void review(row.id, "reject")}>
                    Reject
                  </button>
                  <button type="button" disabled={busyId === row.id} className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => void review(row.id, "approve")}>
                    Approve
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {error ? <p className="mt-3 text-sm text-(--qs-red)">{error}</p> : null}
    </V4Card>
  );
}
