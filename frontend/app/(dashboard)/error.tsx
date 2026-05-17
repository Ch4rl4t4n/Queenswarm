"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function DashboardErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  useEffect(() => {
    console.error("[dashboard:error-boundary]", error);
  }, [error]);

  return (
    <div className="mx-auto mt-16 max-w-2xl rounded-3xl border border-danger/40 bg-black/60 p-8 shadow-[0_0_42px_rgba(255,51,102,0.22)]">
      <p className="font-[family-name:var(--font-poppins)] text-2xl font-semibold text-pollen">dashboard instability detected</p>
      <p className="mt-3 font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
        A runtime error occurred in the cockpit UI. The hive keeps running; reload this section or switch to another panel.
      </p>
      <p className="mt-3 break-all font-mono text-xs text-danger/90">{error.message}</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-xl border border-pollen/60 bg-pollen/10 px-4 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-pollen"
        >
          Retry section
        </button>
        <Link
          href="/dashboard"
          className="rounded-xl border border-cyan/40 px-4 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-cyan"
        >
          Go to dashboard hub
        </Link>
      </div>
      {error.digest ? <p className="mt-4 font-mono text-[10px] text-zinc-600">digest: {error.digest}</p> : null}
    </div>
  );
}
