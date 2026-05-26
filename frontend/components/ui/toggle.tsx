"use client";

import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface ToggleProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange" | "type"> {
  checked: boolean;
  onChange: (next: boolean) => void;
  size?: "sm" | "md";
}

/** Hive-wide glass switch — purple track, amber-glow glass thumb. */

export function Toggle({ checked, onChange, disabled = false, size = "md", className, ...props }: ToggleProps): JSX.Element {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      className={cn(
        "hive-toggle",
        size === "sm" ? "hive-toggle--sm" : "hive-toggle--md",
        checked && "hive-toggle--on",
        disabled && "hive-toggle--disabled",
        className,
      )}
      onClick={() => {
        if (!disabled) {
          onChange(!checked);
        }
      }}
      {...props}
    >
      <span className="hive-toggle-knob" aria-hidden />
    </button>
  );
}
