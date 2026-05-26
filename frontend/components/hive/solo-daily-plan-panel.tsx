"use client";

import Link from "next/link";
import { Loader2, RefreshCw, Target } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { usePlatform } from "@/components/hive/platform-context";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

type SoloLane = "po" | "marketing" | "trading" | "ops";

interface SoloDailyPlanItem {
  id: string;
  lane: SoloLane;
  title: string;
  detail: string;
  href: string | null;
  priority: number;
}

interface SoloDailyPlanSnapshot {
  enabled: boolean;
  items: SoloDailyPlanItem[];
  phase: string;
  links: Record<string, string>;
}

const LANE_LABEL: Record<SoloLane, string> = {
  po: "Bank PO",
  marketing: "Marketing",
  trading: "Trading",
  ops: "Ops",
};

function laneTone(lane: SoloLane): "ok" | "warn" | "gold" | "info" {
  if (lane === "po") return "gold";
  if (lane === "marketing") return "ok";
  if (lane === "trading") return "warn";
  return "info";
}

function SoloDailyPlanPanelInner({ compact = false }: { compact?: boolean }): JSX.Element | null {
  const { soloMode } = usePlatform();
  const [plan, setPlan] = useState<SoloDailyPlanSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [trioBusy, setTrioBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<SoloDailyPlanSnapshot>("solo-operator/daily-plan");
      setPlan(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Daily plan unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (soloMode) {
      void load();
    } else {
      setLoading(false);
    }
  }, [load, soloMode]);

  const runTrio = useCallback(async () => {
    setTrioBusy(true);
    try {
      await hivePostJson("solo-operator/trio/run", {});
      await load();
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Trio run failed");
    } finally {
      setTrioBusy(false);
    }
  }, [load]);

  if (!soloMode) {
    return null;
  }

  if (loading && !plan) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading daily plan…
      </p>
    );
  }

  if (!plan?.enabled || plan.items.length === 0) {
    return null;
  }

  const topItems = plan.items.slice(0, compact ? 3 : 5);

  return (
    <V4Card id="solo-daily-plan" className={cn(compact && "border-pollen/30 bg-pollen/5")}>
      <V4CardHeader
        kicker="Solo"
        title="Dnešný plán"
        description="Max 3–5 akcií — PO, marketing, trading, ops. Simulate-first."
        actions={
          <div className="flex gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={trioBusy}
              onClick={() => void runTrio()}
            >
              {trioBusy ? <Loader2 className="size-3 animate-spin" /> : null}
              Run 3 Bees
            </button>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void load()}>
              <RefreshCw className="size-3" aria-hidden />
            </button>
          </div>
        }
      />
      {err ? <p className="mt-2 text-xs text-[#FF3366]">{err}</p> : null}
      <ol className="mt-4 space-y-2">
        {topItems.map((item, idx) => (
          <li
            key={item.id}
            className="flex flex-wrap items-start gap-2 rounded-lg border border-(--qs-border)/60 bg-black/20 px-3 py-2 text-sm"
          >
            <span className="font-mono text-xs text-(--qs-text-3)">{idx + 1}.</span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <V4Badge tone={laneTone(item.lane)}>{LANE_LABEL[item.lane]}</V4Badge>
                {item.href ? (
                  <Link href={item.href} className="font-medium text-cyan hover:underline">
                    {item.title}
                  </Link>
                ) : (
                  <span className="font-medium text-(--qs-text)">{item.title}</span>
                )}
              </div>
              {!compact ? <p className="mt-1 text-xs text-(--qs-muted)">{item.detail}</p> : null}
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <Link href="/settings/harness#operator-hub" className="text-cyan hover:underline">
          Operator Hub
        </Link>
        <Link href="/integrations?tab=studio" className="text-cyan hover:underline">
          Execution Studio
        </Link>
        <span className="flex items-center gap-1 text-(--qs-text-3)">
          <Target className="size-3" aria-hidden />
          phase: {plan.phase}
        </span>
      </div>
    </V4Card>
  );
}

export const SoloDailyPlanPanel = memo(SoloDailyPlanPanelInner);
SoloDailyPlanPanel.displayName = "SoloDailyPlanPanel";
