"use client";

import Link from "next/link";

interface ForagerProgressCellProps {
  pct: number;
  detail?: string;
  href?: string | null;
  onActivate?: () => void;
}

/** Inline progress bar for forager configuration rows. */
export function ForagerProgressCell({ pct, detail, href, onActivate }: ForagerProgressCellProps): JSX.Element {
  const clamped = Math.max(0, Math.min(100, pct));
  const inner = (
    <div className="v4-progress-cell max-w-md" title={detail || undefined}>
      <div className="v4-progress-track">
        <div className="v4-progress-fill" style={{ width: `${clamped}%` }} />
      </div>
      <span className="v4-progress-pct">{clamped}%</span>
    </div>
  );
  if (href) {
    return (
      <Link href={href} className="block transition hover:opacity-90" title={detail || "Open progress detail"}>
        {inner}
      </Link>
    );
  }
  if (onActivate) {
    return (
      <button
        type="button"
        className="block w-full text-left transition hover:opacity-90"
        title={detail || "Open results report"}
        onClick={onActivate}
      >
        {inner}
      </button>
    );
  }
  return inner;
}
