"use client";

import Link from "next/link";
import { Loader2Icon, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { PatternExplorerPayload } from "@/lib/hive-types";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

function patternTone(count: number): "ok" | "info" | "warn" {
  if (count >= 3) return "ok";
  if (count >= 1) return "info";
  return "warn";
}

function usePatternExplorerData(poll: boolean): {
  loading: boolean;
  err: string | null;
  data: PatternExplorerPayload | null;
  reload: () => Promise<void>;
} {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [data, setData] = useState<PatternExplorerPayload | null>(null);

  const load = useCallback(async () => {
    if (!hasFeature("pattern_explorer")) {
      setLoading(false);
      return;
    }
    try {
      const body = await hiveGet<PatternExplorerPayload>("harness/pattern-explorer");
      setData(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Pattern Explorer unavailable.");
    } finally {
      setLoading(false);
    }
  }, [hasFeature]);

  useEffect(() => {
    void load();
  }, [load]);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    enabled: poll && hasFeature("pattern_explorer"),
    initialDelayMs: DASHBOARD_BOOT_STAGGER_MS.patternExplorer,
  });

  return { loading, err, data, reload: load };
}

function PatternExplorerBody({
  data,
  compact,
}: {
  data: PatternExplorerPayload;
  compact?: boolean;
}): JSX.Element {
  const headline =
    data.unique_patterns_today > 0
      ? `Your swarm used ${data.unique_patterns_today} pattern${data.unique_patterns_today === 1 ? "" : "s"} today`
      : "Pattern Router ready — run a supervisor task to see patterns";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Sparkles className="h-4 w-4 text-cyan" aria-hidden />
        <span className="text-(--qs-text-2)">{headline}</span>
        {data.router_enabled ? <V4Badge tone="ok">Router on</V4Badge> : <V4Badge tone="warn">Router off</V4Badge>}
        {data.forced_reflection_enabled ? <V4Badge tone="info">Reflection</V4Badge> : null}
      </div>

      {data.usage_today.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {data.usage_today.map((row) => (
            <V4Badge key={row.id} tone={patternTone(row.count)}>
              {row.label} ×{row.count}
            </V4Badge>
          ))}
        </div>
      ) : (
        <p className="text-sm text-(--qs-text-3)">
          No patterned sessions in the last {data.window_hours}h — start a Queen mission or routine.
        </p>
      )}

      {!compact ? (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {data.catalog.map((row) => (
            <div key={row.id} className="rounded-lg border border-(--qs-border)/50 bg-black/20 px-3 py-2">
              <p className="text-xs font-semibold text-(--qs-text)">
                #{row.number} {row.label}
              </p>
              <p className="mt-1 text-[10px] text-(--qs-text-3)">{row.summary}</p>
            </div>
          ))}
        </div>
      ) : null}

      {(compact ? data.recent_sessions.slice(0, 1) : data.recent_sessions).map((session) => (
        <div key={session.session_id} className="rounded-xl border border-(--qs-border) bg-black/25 p-3 text-xs text-(--qs-text-2)">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-[11px] text-(--qs-text-3)">
              {session.started_at ? new Date(session.started_at).toLocaleString("sk-SK") : "Recent session"}
            </span>
            <V4Badge tone="info">{session.status}</V4Badge>
          </div>
          {session.goal_preview ? <p className="mt-2 text-sm text-(--qs-text-1)">{session.goal_preview}</p> : null}
          <p className="mt-2">
            Primary: {session.primary.length ? session.primary.join(", ") : "—"}
          </p>
          {session.rationale[0] ? <p className="mt-2 text-(--qs-text-3)">Why: {session.rationale[0]}</p> : null}
        </div>
      ))}
    </div>
  );
}

/** Dashboard panel — which agentic patterns the swarm used and why. */
export function PatternExplorerCard(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const { loading, err, data } = usePatternExplorerData(true);

  if (!hasFeature("pattern_explorer")) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-cyan/20">
      <V4CardHeader
        title="Pattern Explorer"
        description="Agentic design patterns selected by the hive — transparent orchestration."
        actions={
          <Link href="/settings/harness" className="text-xs text-cyan underline-offset-2 hover:underline">
            Full catalog
          </Link>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading patterns…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && data ? <PatternExplorerBody data={data} compact /> : null}
    </V4Card>
  );
}

/** Settings harness page — full 19-pattern catalog + recent sessions. */
export function PatternExplorerSettingsPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const { loading, err, data } = usePatternExplorerData(false);

  if (!hasFeature("pattern_explorer")) {
    return <p className="text-sm text-(--qs-text-3)">Pattern Explorer is not enabled for this workspace.</p>;
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading pattern catalog…
      </p>
    );
  }

  if (err || !data) {
    return <p className="text-sm text-(--qs-red)">{err ?? "Pattern Explorer unavailable."}</p>;
  }

  return (
    <V4Card>
      <V4CardHeader
        title="19 agentic design patterns"
        description="Heuristic Pattern Router selects primary + secondary patterns at every supervisor session start."
      />
      <PatternExplorerBody data={data} />
      <p className="mt-4 text-[10px] text-(--qs-text-3)">Reference: {data.docs_path}</p>
    </V4Card>
  );
}
