import { LeaderboardPageClient } from "@/components/hive/leaderboard-page-client";
import { LEADERBOARD_ENABLED } from "@/lib/feature-flags";

export const dynamic = "force-dynamic";

export default function LeaderboardPage() {
  if (!LEADERBOARD_ENABLED) {
    return (
      <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
          Leaderboard module is disabled. Enable <code>NEXT_PUBLIC_LEADERBOARD_ENABLED=true</code> to open this page.
        </p>
      </div>
    );
  }
  return <LeaderboardPageClient />;
}
