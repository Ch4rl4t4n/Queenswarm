"use client";

import Link from "next/link";

interface SectionRouteErrorProps {
  readonly title: string;
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}

export function SectionRouteError({ title, error, reset }: SectionRouteErrorProps): JSX.Element {
  return (
    <div className="rounded-2xl border border-[#FF3366]/35 bg-[#1a0a14] p-6">
      <h2 className="font-poppins text-lg font-semibold uppercase tracking-[0.08em] text-[#FF3366]">{title} unavailable</h2>
      <p className="mt-2 max-w-2xl text-sm text-zinc-300">
        {error.message.trim() || "The section could not be rendered. Retry the view to restore live data."}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-xl bg-[#FFB800] px-4 py-2 text-sm font-semibold uppercase tracking-[0.06em] text-hive-bg"
        >
          Retry
        </button>
        <Link href="/dashboard" className="rounded-xl border border-cyan/40 px-4 py-2 text-sm font-medium text-cyan">
          Dashboard
        </Link>
        <Link href="/ballroom" className="rounded-xl border border-pollen/40 px-4 py-2 text-sm font-medium text-pollen">
          Ballroom
        </Link>
      </div>
      {error.digest ? <p className="mt-3 font-mono text-[11px] text-zinc-500">digest: {error.digest}</p> : null}
    </div>
  );
}
