"use client";

import confetti from "canvas-confetti";
import { PartyPopperIcon } from "lucide-react";

export function ConfettiTrigger() {
  return (
    <button
      type="button"
      onClick={() =>
        confetti({
          particleCount: 260,
          spread: 94,
          startVelocity: 38,
          origin: { x: 0.5, y: 0.25 },
          colors: ["#FFB800", "#00FFFF", "#00FF88", "#FF00AA"],
        })
      }
      className="inline-flex items-center gap-2 rounded-full border border-success/70 bg-black/35 px-4 py-2 font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.3em] text-success shadow-[0_0_32px_rgba(0,255,136,0.35)]"
    >
      <PartyPopperIcon className="h-4 w-4" aria-hidden /> celebrate verified simulation
    </button>
  );
}
