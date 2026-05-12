"use client";

import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface HiveSwitchProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onClick"> {
  /** Current on/off state. */
  checked: boolean;
  /** Fires when toggle is pressed. */
  onCheckedChange: (next: boolean) => void;
}

/** Pill toggle — amber “on” state per QueenSwarm settings mocks. */
export function HiveSwitch({ checked, onCheckedChange, className, ...props }: HiveSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className={cn(
        "relative h-8 w-[46px] shrink-0 rounded-full border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pollen/55",
        checked ? "border-pollen/65 bg-pollen/40 shadow-[0_0_14px_rgba(255,184,0,0.35)]" : "border-cyan/20 bg-black/55",
        className,
      )}
      onClick={() => onCheckedChange(!checked)}
      {...props}
    >
      <span
        aria-hidden
        className={cn(
          "absolute top-1 h-6 w-6 rounded-full bg-white shadow-md transition-[left]",
          checked ? "left-[22px]" : "left-1",
        )}
      />
    </button>
  );
}
