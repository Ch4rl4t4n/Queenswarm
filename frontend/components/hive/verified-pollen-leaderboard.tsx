"use client";

import { Loader2Icon, TrophyIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { VerifiedPollenLeaderboardRow } from "@/lib/hive-types";

interface VerifiedPollenLeaderboardProps {
  readonly limit?: number;
  readonly compact?: boolean;
}

/** Top bees by simulation-verified pollen (Redis ZSET + Postgres hydrate). */
export function VerifiedPollenLeaderboard({
  limit = 10,
  compact = false,
}: VerifiedPollenLeaderboardProps): JSX.Element {
  const [rows, setRows] = useState<VerifiedPollenLeaderboardRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<VerifiedPollenLeaderboardRow[]>(
        `learning/leaderboard/verified-pollen?limit=${limit}`,
      );
      setRows(payload);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Leaderboard unavailable.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

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

      {!loading && !err && rows.length === 0 ? (
        <p className="text-sm text-(--qs-text-3)">No verified pollen yet — run a verified swarm cycle.</p>
      ) : null}

      <ol className="space-y-2">
        {rows.map((row) => (
          <li
            key={row.agent_id}
            className="flex items-center justify-between gap-3 rounded-xl border border-(--qs-border) bg-black/25 px-3 py-2"
          >
            <div className="flex min-w-0 items-center gap-3">
              <span className="font-mono text-sm tabular-nums text-pollen">#{row.rank}</span>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-(--qs-text)">{row.agent_name}</p>
                <p className="text-xs text-(--qs-text-3)">{row.agent_role}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-mono text-sm tabular-nums text-(--qs-green)">{row.verified_pollen.toFixed(1)}</p>
              <p className="text-[10px] text-(--qs-text-3)">total {Math.round(row.total_pollen)}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
