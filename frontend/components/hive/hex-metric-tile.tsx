"use client";

import type { CSSProperties, ReactNode } from "react";
import { useMemo } from "react";

import { cn } from "@/lib/utils";

/** Tile interior — matches universal agent roster hex. */
export const AGENT_HEX_FILL = "#141424";
export const DEFAULT_AGENT_HEX_STROKE_PX = 3;

/** Swarm lane stroke colors aligned with ``HexAgentCard`` / dashboards. */
export const LANE_HEX_STROKE = {
  scout: "#00E5FF",
  eval: "#FFB800",
  sim: "#FF00AA",
  action: "#00FF88",
} as const;

/**
 * Pointy-top rounded hex (same geometry as ``HexAgentCard``). ViewBox 140×140 user units.
 */
export function RoundedHex({
  strokeColor,
  strokeWidth = DEFAULT_AGENT_HEX_STROKE_PX,
  fill = AGENT_HEX_FILL,
  glowColor,
}: {
  strokeColor: string;
  strokeWidth?: number;
  fill?: string;
  glowColor?: string | undefined;
}): JSX.Element {
  const vb = 140;
  const d = useMemo(() => {
    const cx = vb / 2;
    const cy = vb / 2;
    const r = vb / 2 - strokeWidth - 3;
    const pts: [number, number][] = Array.from({ length: 6 }, (_, i) => {
      const a = (Math.PI / 3) * i - Math.PI / 6;
      return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
    });
    const cr = r * 0.14;
    const n = pts.length;
    let path = "";
    for (let i = 0; i < n; i += 1) {
      const prev = pts[(i - 1 + n) % n]!;
      const curr = pts[i]!;
      const next = pts[(i + 1) % n]!;
      const dx1 = prev[0] - curr[0];
      const dy1 = prev[1] - curr[1];
      const dx2 = next[0] - curr[0];
      const dy2 = next[1] - curr[1];
      const len1 = Math.hypot(dx1, dy1);
      const len2 = Math.hypot(dx2, dy2);
      const rr = Math.min(cr, len1 / 2, len2 / 2);
      const u1 = len1 === 0 ? 0 : rr / len1;
      const u2 = len2 === 0 ? 0 : rr / len2;
      const p1: [number, number] = [curr[0] + dx1 * u1, curr[1] + dy1 * u1];
      const p2: [number, number] = [curr[0] + dx2 * u2, curr[1] + dy2 * u2];
      path +=
        i === 0 ? `M${p1[0].toFixed(2)},${p1[1].toFixed(2)}` : `L${p1[0].toFixed(2)},${p1[1].toFixed(2)}`;
      path += ` Q${curr[0].toFixed(2)},${curr[1].toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)} `;
    }
    path += "Z";
    return path;
  }, [strokeWidth]);

  const svgFilter: CSSProperties | undefined =
    glowColor !== undefined ? { filter: `drop-shadow(0 0 10px ${glowColor}55)` } : undefined;

  return (
    <svg
      className="pointer-events-none absolute inset-0 z-0 h-full w-full"
      viewBox={`0 0 ${vb} ${vb}`}
      preserveAspectRatio="xMidYMid meet"
      style={svgFilter}
      aria-hidden
    >
      <path
        d={d}
        fill={fill}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        vectorEffect="nonScalingStroke"
      />
    </svg>
  );
}

export type HexNumberBadgeVariant = "default" | "solid";

export interface HexNumberBadgeProps {
  /**
   * Step index / counts; shortened when numeric >99. Optional when ``children`` supplies the inset body
   * (DAG hero labels).
   */
  value?: string | number;
  strokeColor: string;
  /** Override digit / label color inside the inset square (defaults to ``strokeColor``). */
  textColor?: string;
  /** Inner square fill (hive void). */
  innerBackground?: string;
  /** SVG path fill behind the inset square (`default` lane look uses ``AGENT_HEX_FILL``). */
  outerFill?: string;
  glowColor?: string;
  /** Footprint matches prior metric chips (~48–52px); scales padding proportionally. */
  sizePx?: number;
  strokeWidth?: number;
  variant?: HexNumberBadgeVariant;
  /** Running step — white pulse dot replaces the inset content. */
  activePulse?: boolean;
  failed?: boolean;
  /** Optional emphasis ring (active DAG node). */
  emphasisRing?: boolean;
  /** Replace inset number with short JetBrains mono text (e.g. DAG hero). */
  children?: ReactNode;
  className?: string;
  /** Typography:mono for cockpit labels. */
  monoLabel?: boolean;
}

/**
 * Compact roster-style hex with centered inset square — same silhouette as agent tiles.
 */
export function HexNumberBadge({
  value,
  strokeColor,
  textColor,
  innerBackground = "#0a0a12",
  outerFill,
  glowColor,
  sizePx = 50,
  strokeWidth = DEFAULT_AGENT_HEX_STROKE_PX,
  variant = "default",
  activePulse = false,
  failed = false,
  emphasisRing = false,
  children,
  className,
  monoLabel = false,
}: HexNumberBadgeProps): JSX.Element {
  const stroke = failed ? "#FF3366" : strokeColor;
  const txt = failed ? "#FF99AA" : (textColor ?? stroke);
  const outer = variant === "solid" ? stroke : (outerFill ?? AGENT_HEX_FILL);
  const insetBody =
    children ??
    (() => {
      if (typeof value === "number" && value > 99) {
        return "99+";
      }
      if (typeof value === "number" || typeof value === "string") {
        return String(value);
      }
      return "";
    })();
  const fontPx = sizePx <= 44 ? 12 : sizePx <= 50 ? 13 : sizePx <= 56 ? 14 : 15;

  return (
    <div
      className={cn(
        "relative shrink-0",
        emphasisRing && "rounded-sm ring-2 ring-white/40 ring-offset-2 ring-offset-[#0c0c14]",
        className,
      )}
      style={{ width: sizePx, height: sizePx }}
    >
      <RoundedHex strokeColor={stroke} strokeWidth={strokeWidth} fill={outer} glowColor={glowColor} />
      <div className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center px-[17%] py-[15%]">
        {activePulse ? (
          <span className="h-2 w-2 rounded-full bg-white shadow-[0_0_8px_#fff]" aria-hidden />
        ) : (
          <div
            className={cn(
              "flex aspect-square h-full max-h-[78%] w-full max-w-[78%] items-center justify-center rounded-[2px] border-2 leading-none",
              monoLabel
                ? "font-[family-name:var(--font-poppins)] font-semibold uppercase tracking-tight"
                : "font-[family-name:var(--font-poppins)] font-bold tabular-nums",
            )}
            style={{
              borderColor: stroke,
              color: txt,
              background: innerBackground,
              fontSize: `${fontPx}px`,
            }}
          >
            {insetBody}
          </div>
        )}
      </div>
    </div>
  );
}
