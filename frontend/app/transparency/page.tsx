import type { Metadata } from "next";
import Link from "next/link";

import { resolveInternalBackendOrigin } from "@/lib/backend-origin";

interface PublicTradingTransparency {
  enabled: boolean;
  generated_at: string;
  mode: string;
  total_equity_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  project_count: number;
  recent_fills: Array<{ symbol: string; side: string }>;
  disclaimer: string;
}

async function fetchTransparency(): Promise<PublicTradingTransparency | null> {
  const origin = resolveInternalBackendOrigin();
  try {
    const res = await fetch(`${origin}/api/v1/marketing/trading-transparency`, {
      next: { revalidate: 120 },
    });
    if (!res.ok) return null;
    return (await res.json()) as PublicTradingTransparency;
  } catch {
    return null;
  }
}

export const metadata: Metadata = {
  title: "Paper Trading Transparency · Queenswarm",
  description: "Read-only paper trading performance — simulated fills, no secrets.",
};

export default async function TransparencyPage(): Promise<JSX.Element> {
  const data = await fetchTransparency();
  const enabled = data?.enabled ?? false;
  const pnlPositive = (data?.total_pnl_usd ?? 0) >= 0;

  return (
    <main className="min-h-screen bg-[#050510] px-4 py-16 text-(--qs-text)">
      <div className="mx-auto max-w-2xl">
        <p className="font-[family-name:var(--font-space-grotesk)] text-xs uppercase tracking-[0.2em] text-pollen">
          Queenswarm · verified swarm
        </p>
        <h1 className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold leading-tight md:text-4xl">
          Paper trading transparency
        </h1>
        <p className="mt-4 text-base text-(--qs-text-2)">
          Read-only aggregate from our paper lane — no live money, no operator secrets.
        </p>

        {!enabled || !data ? (
          <p className="mt-8 rounded-xl border border-(--qs-border) bg-white/5 p-4 text-sm text-(--qs-text-3)">
            Transparency feed is temporarily unavailable.
          </p>
        ) : (
          <>
            <dl className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3 text-center">
                <dt className="text-[10px] uppercase text-(--qs-text-3)">Mode</dt>
                <dd className="mt-1 font-mono text-lg uppercase text-cyan">{data.mode}</dd>
              </div>
              <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3 text-center">
                <dt className="text-[10px] uppercase text-(--qs-text-3)">Equity</dt>
                <dd className="mt-1 font-mono text-lg text-(--qs-text)">${data.total_equity_usd.toFixed(2)}</dd>
              </div>
              <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3 text-center">
                <dt className="text-[10px] uppercase text-(--qs-text-3)">P&amp;L</dt>
                <dd className={`mt-1 font-mono text-lg ${pnlPositive ? "text-[#00FF88]" : "text-[#FF3366]"}`}>
                  ${data.total_pnl_usd.toFixed(2)}
                </dd>
              </div>
              <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3 text-center">
                <dt className="text-[10px] uppercase text-(--qs-text-3)">Return</dt>
                <dd className={`mt-1 font-mono text-lg ${pnlPositive ? "text-[#00FF88]" : "text-[#FF3366]"}`}>
                  {data.total_pnl_pct.toFixed(2)}%
                </dd>
              </div>
            </dl>

            <p className="mt-4 text-xs text-(--qs-text-3)">
              {data.project_count} paper project(s) · updated {new Date(data.generated_at).toLocaleString()}
            </p>

            {data.recent_fills.length > 0 ? (
              <section className="mt-8">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-(--qs-text-3)">Recent fills</h2>
                <ul className="mt-3 space-y-2">
                  {data.recent_fills.map((fill, index) => (
                    <li
                      key={`${fill.symbol}-${fill.side}-${index}`}
                      className="flex justify-between rounded-lg border border-(--qs-border) bg-white/5 px-3 py-2 font-mono text-sm"
                    >
                      <span className="text-cyan">{fill.symbol}</span>
                      <span className="uppercase text-pollen">{fill.side}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <p className="mt-8 text-xs text-(--qs-text-3)">{data.disclaimer}</p>
          </>
        )}

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/login" className="qs-btn qs-btn--primary">
            Join the hive
          </Link>
          <Link href="/swarms/new?template=polymarket-trading" className="qs-btn qs-btn--ghost">
            Polymarket swarm template
          </Link>
        </div>
      </div>
    </main>
  );
}
