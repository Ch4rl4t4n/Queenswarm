"use client";

import Link from "next/link";

/** Dashboard toolbar aligned with Figma “Live Agent Swarm” actions. */
export function LiveSwarmToolbar() {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link href="/agents" className="qs-btn qs-btn--ghost qs-btn--sm uppercase tracking-wide">
        + Add agent
      </Link>
      <Link href="/simulations" className="qs-btn qs-btn--primary qs-btn--sm uppercase tracking-wide">
        Run simulation
      </Link>
    </div>
  );
}
