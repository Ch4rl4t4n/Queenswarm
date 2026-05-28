"use client";

import { Loader2, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface LiveLaneStep {
  id: string;
  lane: string;
  label: string;
  status: string;
  detail: string;
}

interface LiveLaneAction {
  id: string;
  label: string;
  detail: string;
  priority: string;
  href?: string | null;
}

interface LiveLaneSnapshot {
  enabled: boolean;
  progress_pct: number;
  polymarket_prep_pct: number;
  publish_prep_pct: number;
  trading_live_flag: boolean;
  publish_live_flag: boolean;
  ready_for_trading_live: boolean;
  ready_for_publish_live: boolean;
  steps: LiveLaneStep[];
  actions: LiveLaneAction[];
}

interface LiveLanePreflight {
  trading: { allowed: boolean; blockers: string[] };
  publish: { allowed: boolean; blockers: string[] };
}

export interface ExecutionStudioLiveLanePanelProps {
  onError: (message: string | null) => void;
}

function ExecutionStudioLiveLanePanelInner({ onError }: ExecutionStudioLiveLanePanelProps) {
  const [snapshot, setSnapshot] = useState<LiveLaneSnapshot | null>(null);
  const [preflight, setPreflight] = useState<LiveLanePreflight | null>(null);
  const [loading, setLoading] = useState(true);
  const [preflightLoading, setPreflightLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<LiveLaneSnapshot>("live-lane");
      setSnapshot(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setSnapshot(null);
        return;
      }
      onError(err instanceof Error ? err.message : "Live lane snapshot failed.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  const runPreflight = useCallback(async () => {
    setPreflightLoading(true);
    onError(null);
    try {
      const data = await hivePostJson<{ trading: LiveLanePreflight["trading"]; publish: LiveLanePreflight["publish"] }>(
        "live-lane/preflight",
        {},
      );
      setPreflight(data);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Preflight failed.");
    } finally {
      setPreflightLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!loading && snapshot && !snapshot.enabled) {
    return null;
  }

  return (
    <div id="live-lane" className="qs-bubble qs-bubble--tint-magenta shrink-0 space-y-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-[#FF00AA]" aria-hidden />
          <h3 className="font-heading text-sm font-semibold text-(--qs-text)">Live Lane Prep</h3>
        </div>
        <HiveRefreshButton busy={loading} onClick={() => void load()} />
      </div>

      <p className="text-xs text-(--qs-text-3)">
        Polymarket trading + social publish — simulate-first. Live flags off until operator env review.
      </p>

      {snapshot ? (
        <>
          <div className="flex flex-wrap gap-2 text-xs">
            <V4Badge tone={snapshot.progress_pct >= 80 ? "ok" : "warn"}>{snapshot.progress_pct}% prep</V4Badge>
            <V4Badge tone={snapshot.trading_live_flag ? "err" : "info"}>
              Trading live {snapshot.trading_live_flag ? "ON" : "OFF"}
            </V4Badge>
            <V4Badge tone={snapshot.publish_live_flag ? "err" : "info"}>
              Publish live {snapshot.publish_live_flag ? "ON" : "OFF"}
            </V4Badge>
          </div>

          <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
            {snapshot.steps.slice(0, 8).map((step) => (
              <li key={step.id} className="rounded bg-black/20 px-2 py-1">
                <span className="uppercase text-[10px] text-cyan">{step.lane}</span>
                <span className="text-(--qs-text)"> · {step.label}</span>
                <V4Badge tone={step.status === "done" ? "ok" : "warn"}>{step.status}</V4Badge>
              </li>
            ))}
          </ul>

          {snapshot.actions.length > 0 ? (
            <ul className="space-y-1 text-xs">
              {snapshot.actions.slice(0, 4).map((action) => (
                <li key={action.id} className="flex justify-between gap-2 rounded border border-white/10 p-2">
                  <span className="text-(--qs-text)">{action.label}</span>
                  {action.href ? (
                    <Link href={action.href} className="text-cyan hover:underline">
                      Open
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}

          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm"
            disabled={preflightLoading}
            onClick={() => void runPreflight()}
          >
            {preflightLoading ? <Loader2 className="size-3 animate-spin" /> : null}
            Run preflight (dry-run)
          </button>

          {preflight ? (
            <div className="space-y-2 rounded border border-white/10 bg-black/20 p-2 text-[11px]">
              <p>
                Trading:{" "}
                <V4Badge tone={preflight.trading.allowed ? "ok" : "err"}>
                  {preflight.trading.allowed ? "ready" : "blocked"}
                </V4Badge>
              </p>
              {!preflight.trading.allowed ? (
                <ul className="list-disc pl-4 text-(--qs-text-3)">
                  {preflight.trading.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              ) : null}
              <p>
                Publish:{" "}
                <V4Badge tone={preflight.publish.allowed ? "ok" : "err"}>
                  {preflight.publish.allowed ? "ready" : "blocked"}
                </V4Badge>
              </p>
              {!preflight.publish.allowed ? (
                <ul className="list-disc pl-4 text-(--qs-text-3)">
                  {preflight.publish.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export const ExecutionStudioLiveLanePanel = memo(ExecutionStudioLiveLanePanelInner);
