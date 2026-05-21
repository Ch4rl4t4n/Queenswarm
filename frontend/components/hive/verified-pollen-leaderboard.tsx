"use client";

import { Loader2Icon, TrophyIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { BeeBadgeProfile, VerifiedPollenLeaderboardRow } from "@/lib/hive-types";

interface VerifiedPollenLeaderboardProps {
  readonly limit?: number;
  readonly compact?: boolean;
}

/** Top bees by simulation-verified pollen (Redis ZSET + Postgres hydrate). */
export function VerifiedPollenLeaderboard({
  limit = 10,
  compact = false,
}: VerifiedPollenLeaderboardProps): JSX.Element {
  const { hasFeature } = usePlatform();
  const gamified = hasFeature("bee_gamification");
  const [rows, setRows] = useState<VerifiedPollenLeaderboardRow[]>([]);
  const [badgeByAgent, setBadgeByAgent] = useState<Map<string, BeeBadgeProfile["badges"]>>(new Map());
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const requests: [
        Promise<VerifiedPollenLeaderboardRow[]>,
        Promise<BeeBadgeProfile[]> | null,
      ] = [
        hiveGet<VerifiedPollenLeaderboardRow[]>(`learning/leaderboard/verified-pollen?limit=${limit}`),
        gamified ? hiveGet<BeeBadgeProfile[]>(`learning/bee-badges?limit=${Math.max(limit, 24)}`) : null,
      ];
      const [payload, badgePayload] = await Promise.all([
        requests[0],
        requests[1] ?? Promise.resolve([] as BeeBadgeProfile[]),
      ]);
      setRows(payload);
      if (gamified && badgePayload.length > 0) {
        const map = new Map<string, BeeBadgeProfile["badges"]>();
        for (const profile of badgePayload) {
          map.set(profile.agent_id, profile.badges);
        }
        setBadgeByAgent(map);
      } else {
        setBadgeByAgent(new Map());
      }
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Leaderboard unavailable.");
      setRows([]);
      setBadgeByAgent(new Map());
    } finally {
      setLoading(false);
    }
  }, [gamified, limit]);

  useEffect(() => {
    void load();
  }, [load]);

  const visibleRows = useMemo(() => rows.slice(0, limit), [limit, rows]);

  return (
    <section className={compact ? "space-y-3" : "v4-learning-panel space-y-4 p-4"}>
      <V4CardHeader
        as="h3"
        title="Verified pollen leaderboard"
        description="Bees ranked by simulation-gated rewards only — social proof for premium skills."
        actions={
          <V4Badge tone="gold">
            <TrophyIcon className="mr-1 inline h-3 w-3" aria-hidden /> live
          </V4Badge>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading ranks…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && visibleRows.length === 0 ? (
        <p className="text-sm text-(--qs-text-3)">No verified pollen yet — run a verified swarm cycle.</p>
      ) : null}

      <ol className="space-y-2">
        {visibleRows.map((row) => {
          const badges = badgeByAgent.get(row.agent_id) ?? [];
          return (
            <li
              key={row.agent_id}
              className="flex items-center justify-between gap-3 rounded-xl border border-(--qs-border) bg-black/25 px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="font-mono text-sm tabular-nums text-pollen">#{row.rank}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-(--qs-text)">{row.agent_name}</p>
                  <p className="text-xs text-(--qs-text-3)">{row.agent_role}</p>
                  {gamified && badges.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {badges.slice(0, 3).map((badge) => (
                        <span
                          key={badge.id}
                          className="rounded-full border border-(--qs-border) bg-black/40 px-1.5 py-0.5 text-[10px] text-(--qs-text-2)"
                          title={badge.description}
                        >
                          {badge.emoji} {badge.label}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              <div className="text-right">
                <p className="font-mono text-sm tabular-nums text-(--qs-green)">{row.verified_pollen.toFixed(1)}</p>
                <p className="text-[10px] text-(--qs-text-3)">total {Math.round(row.total_pollen)}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
