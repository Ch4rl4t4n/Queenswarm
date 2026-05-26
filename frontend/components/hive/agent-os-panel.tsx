"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Brain, Loader2, RefreshCw } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AgentOsAction {
  id: string;
  label: string;
  detail: string;
  priority: string;
  href: string | null;
}

interface AgentOsSnapshot {
  enabled: boolean;
  generated_at: string;
  cross_swarm: {
    enabled: boolean;
    source_domain: string;
    suggestions: Array<{ name: string; similarity: number; rationale: string }>;
  };
  imitation_v2: {
    enabled: boolean;
    verified_outcomes: number;
    ready: boolean;
    suggestions: Array<{ name: string; similarity: number; detail: string }>;
  };
  behavioral_proposals: {
    enabled: boolean;
    proposals: Array<{ id: string; proposal: string; priority: string }>;
  };
  last_analysis: {
    consensus: string;
    consensus_strength: number;
    recommend_execute: boolean;
  } | null;
  actions: AgentOsAction[];
  links: Record<string, string>;
}

function actionTone(priority: string): "ok" | "warn" | "err" | "info" {
  if (priority === "high") return "err";
  if (priority === "medium") return "warn";
  return "info";
}

function AgentOsPanelInner() {
  const [snapshot, setSnapshot] = useState<AgentOsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<AgentOsSnapshot>("agent-os");
      setSnapshot(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Agent OS unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !snapshot) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Agent OS…
      </p>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card id="agent-os">
      <V4CardHeader
        kicker="Autonomy layer"
        title="Agent OS"
        description="Cross-swarm learning, imitation v2, overnight behavioral proposals."
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <V4Badge tone="info">
          <Brain className="mr-1 inline size-3" aria-hidden />
          P8
        </V4Badge>
        <V4Badge tone={snapshot.imitation_v2.ready ? "ok" : "warn"}>
          Imitation {snapshot.imitation_v2.verified_outcomes}/3
        </V4Badge>
        {snapshot.last_analysis ? (
          <V4Badge tone={snapshot.last_analysis.recommend_execute ? "ok" : "info"}>
            Analysis: {snapshot.last_analysis.consensus}
          </V4Badge>
        ) : null}
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void load()}>
          <RefreshCw className={cn("size-4", loading && "animate-spin")} aria-hidden />
          Refresh
        </button>
      </div>

      {snapshot.behavioral_proposals.proposals.length > 0 ? (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-semibold uppercase text-pollen">Overnight behavioral proposals</p>
          <ul className="space-y-1">
            {snapshot.behavioral_proposals.proposals.map((p) => (
              <li key={p.id} className="rounded border border-(--qs-border)/60 bg-black/20 px-3 py-2 text-xs text-(--qs-text-2)">
                {p.proposal}
              </li>
            ))}
          </ul>
          <Link href="/settings/harness" className="text-xs text-cyan hover:text-pollen">
            Merge into behavioral memory →
          </Link>
        </div>
      ) : null}

      {snapshot.actions.length > 0 ? (
        <ul className="space-y-2">
          {snapshot.actions.map((action) => (
            <li
              key={action.id}
              className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-(--qs-text)">{action.label}</span>
                  <V4Badge tone={actionTone(action.priority)}>{action.priority}</V4Badge>
                </div>
                <p className="mt-0.5 text-xs text-(--qs-muted)">{action.detail}</p>
              </div>
              {action.href ? (
                <Link href={action.href} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0">
                  Go
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-(--qs-text-3)">Run simulate-first workflows to unlock autonomy suggestions.</p>
      )}
    </V4Card>
  );
}

export const AgentOsPanel = memo(AgentOsPanelInner);
AgentOsPanel.displayName = "AgentOsPanel";

const LazyAgentOsPanel = dynamic(() => Promise.resolve({ default: AgentOsPanel }), {
  ssr: false,
  loading: () => (
    <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
      <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Agent OS…
    </p>
  ),
});

export { LazyAgentOsPanel };
