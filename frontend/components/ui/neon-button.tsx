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
  primary: "qs-btn--primary",
  secondary: "qs-btn--secondary",
  ghost: "qs-btn--ghost",
  danger: "qs-btn--danger",
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
        "qs-btn focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00ffff]/55 disabled:pointer-events-none",
        VARIANTS[variant],
        className,
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}
