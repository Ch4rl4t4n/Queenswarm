"use client";

import Link from "next/link";

import { NeonButton } from "@/components/ui/neon-button";

/** Dashboard toolbar aligned with Figma “Live Agent Swarm” actions. */
export function LiveSwarmToolbar() {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <NeonButton variant="ghost" asChild className="uppercase tracking-wide">
        <Link href="/agents">+ Add agent</Link>
      </NeonButton>
      <NeonButton variant="primary" asChild className="uppercase tracking-wide">
        <Link href="/simulations">Run simulation</Link>
      </NeonButton>
    </div>
  );
}
