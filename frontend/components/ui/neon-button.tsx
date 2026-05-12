"use client";

import { Slot } from "@radix-ui/react-slot";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export type NeonVariant = "primary" | "secondary" | "ghost" | "danger";

interface NeonButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: NeonVariant;
  asChild?: boolean;
  children: ReactNode;
}

const VARIANTS: Record<NeonVariant, string> = {
  primary:
    "border border-pollen/50 bg-pollen/15 text-pollen shadow-[0_0_28px_rgba(255,184,0,0.42)] hover:bg-pollen/25 hover:shadow-[0_0_36px_rgba(255,184,0,0.55)]",
  secondary:
    "border border-data/45 bg-data/10 text-data shadow-[0_0_22px_rgba(0,255,255,0.28)] hover:border-data hover:bg-data/15",
  ghost:
    "border border-cyan/25 bg-transparent text-cyan hover:border-pollen/40 hover:text-pollen hover:shadow-[0_0_18px_rgba(255,184,0,0.22)]",
  danger:
    "border border-danger/55 bg-danger/10 text-danger shadow-[0_0_20px_rgba(255,51,102,0.35)] hover:bg-danger/20",
};

/** Neon-glow action — supports Radix `asChild` for links. */
export function NeonButton({
  variant = "primary",
  className,
  asChild = false,
  children,
  type = "button",
  ...props
}: NeonButtonProps) {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      type={asChild ? undefined : type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm font-semibold tracking-wide transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-data disabled:pointer-events-none disabled:opacity-45",
        VARIANTS[variant],
        className,
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}
