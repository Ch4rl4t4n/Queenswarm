"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type GlowColor = "amber" | "cyan" | "green" | "magenta" | "red";

export type CardSize = "sm" | "md" | "lg";

const glow: Record<GlowColor, string> = {
  amber:
    "shadow-[0_0_18px_#FFB80055] border-[#FFB800]/30 hover:shadow-[0_0_28px_#FFB80088]",
  cyan:
    "shadow-[0_0_18px_#00FFFF55] border-[#00FFFF]/30 hover:shadow-[0_0_28px_#00FFFF88]",
  green:
    "shadow-[0_0_18px_#00FF8855] border-[#00FF88]/30 hover:shadow-[0_0_28px_#00FF8888]",
  magenta:
    "shadow-[0_0_18px_#FF00AA55] border-[#FF00AA]/30 hover:shadow-[0_0_28px_#FF00AA88]",
  red:
    "shadow-[0_0_18px_#FF336655] border-[#FF3366]/30 hover:shadow-[0_0_28px_#FF336688]",
};

const sizes: Record<CardSize, string> = {
  sm: "w-[90px] h-[104px]",
  md: "w-[130px] h-[150px]",
  lg: "w-[170px] h-[196px]",
};

export function HexCard({
  children,
  className,
  glowColor = "amber",
  size = "md",
  onClick,
}: {
  children: ReactNode;
  className?: string;
  glowColor?: GlowColor;
  size?: CardSize;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      tabIndex={onClick ? 0 : undefined}
      className={cn(
        "relative flex flex-col items-center justify-center bg-[#0d0d2b] border",
        "transition-all duration-300 hover:scale-105 cursor-pointer select-none",
        "[clip-path:polygon(50%_0%,100%_25%,100%_75%,50%_100%,0%_75%,0%_25%)]",
        glow[glowColor],
        sizes[size],
        className,
      )}
    >
      {children}
    </div>
  );
}
