import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Polymarket Trading · Queenswarm",
  description: "Real-money Polymarket prediction markets — evaluator + live executor swarms.",
};

export default function TransparencyPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[#050510] px-4 py-16 text-(--qs-text)">
      <div className="mx-auto max-w-2xl">
        <p className="font-[family-name:var(--font-space-grotesk)] text-xs uppercase tracking-[0.2em] text-pollen">
          Queenswarm · prediction markets
        </p>
        <h1 className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold leading-tight md:text-4xl">
          Polymarket live lane
        </h1>
        <p className="mt-4 text-base text-(--qs-text-2)">
          Paper trading simulation was removed. Queenswarm supports real USDC on Polymarket via separate
          evaluator and executor swarms — operator approval required for every live order.
        </p>

        <div className="mt-8 rounded-xl border border-(--qs-border) bg-white/5 p-4 text-sm text-(--qs-text-3)">
          <p className="font-semibold text-(--qs-text)">Two swarms (by design)</p>
          <ul className="mt-3 list-inside list-disc space-y-2">
            <li>
              <strong>Prediction Evaluator</strong> — research + consensus only, no orders
            </li>
            <li>
              <strong>Live Executor</strong> — signed CLOB orders after risk gate + your approval
            </li>
          </ul>
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/login" className="qs-btn qs-btn--primary">
            Open Trading Cockpit
          </Link>
          <Link href="/swarms/new?template=polymarket-prediction-evaluator" className="qs-btn qs-btn--ghost">
            Spawn evaluator swarm
          </Link>
          <Link href="/swarms/new?template=polymarket-trading" className="qs-btn qs-btn--ghost">
            Spawn live executor
          </Link>
        </div>
      </div>
    </main>
  );
}
