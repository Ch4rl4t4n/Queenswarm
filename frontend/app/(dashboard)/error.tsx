"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  useEffect(() => {
    console.error("[dashboard:error]", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div
        className="font-poppins text-xl font-semibold uppercase tracking-[0.12em]"
        style={{ color: "#FF3366", textShadow: "0 0 18px rgba(255, 51, 102, 0.45)" }}
      >
        Hive link severed
      </div>
      <p className="max-w-md text-sm text-zinc-400">
        {error.message.trim() ||
          "Something failed while rendering this area of the cockpit. Retry or return home."}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-xl bg-[#FFB800] px-5 py-2 text-sm font-semibold uppercase tracking-[0.06em] text-[#050510] shadow-[0_0_22px_rgba(255,184,0,0.35)]"
        >
          Retry
        </button>
        <Link
          href="/"
          className="rounded-xl border border-cyan-500/40 px-4 py-2 text-sm font-medium text-[#00FFFF]"
        >
          Dashboard
        </Link>
      </div>
      {error.digest ? (
        <p className="font-mono text-[10px] text-zinc-600">digest: {error.digest}</p>
      ) : null}
    </div>
  );
}
