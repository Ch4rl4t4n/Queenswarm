"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import { useMemo } from "react";

import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

const SWARM_STROKE: Record<"scout" | "eval" | "sim" | "action", string> = {
  scout: "#00E5FF",
  eval: "#FFB800",
  sim: "#FF00AA",
  action: "#00FF88",
};

const AMBER_STROKE = "#FFB800";

const HEX_FILL = "#141424";
/** Aligned with ``--qs-bubble-border-width``; SVG path uses ``vectorEffect="nonScalingStroke"`` so rim stays uniform when ``tilePx`` changes. */
const DEFAULT_STROKE_WIDTH = 3;

const STATUS_COLORS: Record<"live" | "idle" | "paused" | "error", string> = {
  live: "#00FF88",
  idle: "#FFB800",
  paused: "#FF3366",
  error: "#FF3366",
};

export function swarmKeyFromAgent(agent: AgentRow): keyof typeof SWARM_STROKE | "unassigned" {
  return hexSwarmLaneKey(agent) ?? "unassigned";
}

function filledHiveId(value: unknown): boolean {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

/** Swarm-linked for stroke color: ``sub_swarm_id`` OR ``swarm_id`` (Phase R). */
function hiveAnchored(agent: AgentRow): boolean {
  const sub = (agent as AgentRow & { sub_swarm_id?: string | null }).sub_swarm_id;
  return filledHiveId(sub) || filledHiveId(agent.swarm_id);
}

function rawSwarmKeywordBlob(agent: AgentRow): string {
  const extended = agent as AgentRow & {
    swarm_type?: string | null;
    swarm?: { name?: string } | null;
  };
  const parts = [
    extended.swarm_type,
    extended.swarm?.name,
    agent.swarm_name,
    agent.swarm_purpose,
  ].filter(Boolean);
  return parts.join(" ").toLowerCase();
}

function hexSwarmLaneKey(agent: AgentRow): keyof typeof SWARM_STROKE | null {
  if (!hiveAnchored(agent)) {
    return null;
  }
  const raw = rawSwarmKeywordBlob(agent);
  if (raw.includes("scout")) return "scout";
  if (raw.includes("eval")) return "eval";
  if (raw.includes("sim")) return "sim";
  if (raw.includes("action")) return "action";
  return null;
}

function statusVisual(status: string): { tone: keyof typeof STATUS_COLORS; pulse: boolean } {
  const u = status.toUpperCase();
  if (u === "RUNNING" || u === "BUSY" || u === "ACTIVE") {
    return { tone: "live", pulse: true };
  }
  if (u === "PAUSED") {
    return { tone: "paused", pulse: false };
  }
  if (u === "ERROR" || u === "OFFLINE") {
    return { tone: "error", pulse: false };
  }
  return { tone: "idle", pulse: false };
}

function formatRole(role: string): string {
  const cleaned = role.replaceAll("_", " ").trim();
  if (!cleaned) {
    return "WorkerBee";
  }
  return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)}`;
}

function pctScore(s: number | undefined): number {
  if (s === undefined || Number.isNaN(s)) {
    return 0;
  }
  return Math.round(Math.min(1, Math.max(0, s)) * 100);
}

function pollenDisplay(points: number): string {
  const n = Number(points) || 0;
  if (n > 999) {
    return `${(n / 1000).toFixed(1)}k`;
  }
  return n.toFixed(n >= 100 ? 0 : 1);
}

/**
 * Pointy-top rounded hex (~14% corner smoothing). Path in 140×140 user units; SVG scales to parent tile.
 *
 * Args:
 *     strokeColor: SVG stroke (lane color).
 *     strokeWidth: Stroke thickness in user units.
 *     fill: Interior fill.
 *     glowColor: Optional glow via ``drop-shadow`` (running bees).
 */
function RoundedHex({
  strokeColor,
  strokeWidth = DEFAULT_STROKE_WIDTH,
  fill = HEX_FILL,
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
    glowColor !== undefined ? { filter: `drop-shadow(0 0 8px ${glowColor}66)` } : undefined;

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

interface HexAgentCardProps {
  agent: AgentRow;
  onClick?: () => void;
  href?: string;
  showPerformance?: boolean;
  renderAsDiv?: boolean;
  className?: string;
  /** Larger / smaller tile than default 140×140 (Phase W hierarchy). */
  tilePx?: number;
  /** Queen / orchestrator affordance — amber stroke + crown. */
  isQueen?: boolean;
}

/**
 * Agent roster hex — rounded pointy-top hex via SVG stroke; amber when not swarm-colored.
 */
export function HexAgentCard({
  agent,
  onClick,
  href,
  showPerformance = false,
  renderAsDiv = false,
  className,
  tilePx,
  isQueen = false,
}: HexAgentCardProps): JSX.Element {
  const sk = swarmKeyFromAgent(agent);
  const borderColor = isQueen ? AMBER_STROKE : sk === "unassigned" ? AMBER_STROKE : SWARM_STROKE[sk];
  const pollenAccent = borderColor;

  const sv = statusVisual(agent.status ?? "");
  const statusColor = STATUS_COLORS[sv.tone];
  const pollenVal = pollenDisplay(agent.pollen_points ?? 0);
  const scoreP = pctScore(agent.performance_score);
  const idle = (agent.status ?? "").toUpperCase() === "IDLE";
  /** Running / busy — Phase R “active” glow matches border hue. */
  const glowHue = sv.pulse ? borderColor : undefined;

  const inner = (
    <>
      <RoundedHex strokeColor={borderColor} strokeWidth={DEFAULT_STROKE_WIDTH} fill={HEX_FILL} glowColor={glowHue} />
      <div className="qs-hex__inner">
        {isQueen ? (
          <span className="-mb-0.5 text-sm leading-none" aria-hidden>
            👑
          </span>
        ) : null}
        <div
          className={cn("qs-hex__dot", sv.pulse && "qs-pulse")}
          style={{
            background: statusColor,
            boxShadow: sv.pulse ? `0 0 6px ${statusColor}` : "none",
          }}
        />
        <div className="qs-hex__name">{agent.name}</div>
        <div className="qs-hex__role">{formatRole(agent.role)}</div>
        <div className="qs-hex__pollen" style={{ color: pollenAccent }}>
          ◈ {pollenVal}
        </div>
        {showPerformance && scoreP > 0 ? (
          <div className="mt-1 h-1 w-[90px] max-w-[min(90px,85%)] overflow-hidden rounded-full bg-black/55">
            <div className="h-full rounded-full" style={{ width: `${scoreP}%`, backgroundColor: pollenAccent }} />
          </div>
        ) : null}
      </div>
    </>
  );

  const px = tilePx ?? 140;
  const scalable = px !== 140;
  const fixedTile: CSSProperties & { "--qs-hex-scaled"?: string } = scalable
    ? {
        width: px,
        height: px,
        minWidth: px,
        minHeight: px,
        maxWidth: px,
        maxHeight: px,
        flexShrink: 0,
        "--qs-hex-scaled": `${px}px`,
      }
    : {
        width: 140,
        height: 140,
        minWidth: 140,
        minHeight: 140,
        maxWidth: 140,
        maxHeight: 140,
        flexShrink: 0,
      };

  const rootClass = cn("qs-hex group relative", scalable && "qs-hex--scalable", idle && "opacity-[0.97]", className);

  if (href) {
    return (
      <Link href={href} prefetch={false} className={rootClass} style={fixedTile}>
        {inner}
      </Link>
    );
  }

  if (renderAsDiv) {
    return (
      <div className={rootClass} style={fixedTile}>
        {inner}
      </div>
    );
  }

  return (
    <button type="button" className={rootClass} style={fixedTile} onClick={onClick}>
      {inner}
    </button>
  );
}
