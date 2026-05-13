"use client";

import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface ToggleProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange" | "type"> {
  checked: boolean;
  onChange: (next: boolean) => void;
  size?: "sm" | "md";
}

/** Hive-wide switch — violet on-track (Phase W), sliding white thumb with optional check glyph. */

export function Toggle({ checked, onChange, disabled = false, size = "md", className, ...props }: ToggleProps): JSX.Element {
  const w = size === "sm" ? 40 : 48;
  const h = size === "sm" ? 22 : 26;
  const dotSize = size === "sm" ? 16 : 20;
  const dotOffset = 3;

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      className={cn(
        "relative shrink-0 border-0 p-0 outline-none transition-colors duration-200 ease-out focus-visible:ring-2 focus-visible:ring-violet-500/55 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0c0c14]",
        checked ? "bg-[#7C3AED]" : "bg-[#3a3a5a]",
        disabled ? "cursor-not-allowed opacity-40" : "cursor-pointer",
        className,
      )}
      style={{
        width: w,
        height: h,
        borderRadius: h / 2,
      }}
      onClick={() => {
        if (!disabled) {
          onChange(!checked);
        }
      }}
      {...props}
    >
      <span
        className="absolute flex items-center justify-center rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.3)] transition-[left] duration-200 ease-out"
        style={{
          top: dotOffset,
          left: checked ? w - dotSize - dotOffset : dotOffset,
          width: dotSize,
          height: dotSize,
        }}
        aria-hidden
      >
        {checked ? (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
            <polyline
              points="2,5 4,7.5 8,3"
              stroke="#7C3AED"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : null}
      </span>
    </button>
  );
}
