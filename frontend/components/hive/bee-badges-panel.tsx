"use client";

import { Loader2Icon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { BeeBadgeProfile } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface BeeBadgesPanelProps {
  readonly limit?: number;
  readonly compact?: boolean;
}

function badgeTone(tier: string): "ok" | "warn" | "gold" | "info" {
  if (tier === "gold") return "gold";
  if (tier === "silver") return "warn";
  if (tier === "bronze") return "info";
  return "ok";
}

/** Verified-workflow badges — gamification layer on pollen leaderboard. */
export function BeeBadgesPanel({ limit = 8, compact = false }: BeeBadgesPanelProps): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [rows, setRows] = useState<BeeBadgeProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<BeeBadgeProfile[]>(`learning/bee-badges?limit=${limit}`);
      setRows(payload);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Bee badges unavailable.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    if (!hasFeature("bee_gamification")) return;
    void load();
  }, [hasFeature, load]);

  if (!hasFeature("bee_gamification")) {
    return null;
  }

  return (
    <section className={cn(compact ? "space-y-3" : "v4-learning-panel space-y-4 p-4")}>
      <V4CardHeader
        as="h3"
        title="Bee badges"
        description="Earned from simulation-verified workflows — not raw chat output."
        actions={
          <V4Badge tone="ok">
            <SparklesIcon className="mr-1 inline h-3 w-3" aria-hidden /> gamified
          </V4Badge>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading badges…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && rows.length === 0 ? (
        <p className="text-sm text-(--qs-text-3)">No badges yet — complete a verified swarm cycle.</p>
      ) : null}

      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {rows.map((row) => (
          <li key={row.agent_id} className="rounded-xl border border-(--qs-border) bg-black/25 p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-(--qs-text)">{row.agent_name}</p>
                <p className="text-xs text-(--qs-text-3)">
                  {row.agent_role} · {row.verified_pollen.toFixed(1)} verified · {row.performance_pct}% perf
                </p>
              </div>
              <span className="font-mono text-xs text-pollen">{row.badge_count}★</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {row.badges.map((badge) => (
                <span key={badge.id} title={badge.description}>
                  <V4Badge tone={badgeTone(badge.tier)}>
                    {badge.emoji} {badge.label}
                  </V4Badge>
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
