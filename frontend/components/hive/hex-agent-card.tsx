"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import { useMemo } from "react";

import { agentHiveLane, type AgentHiveLane } from "@/lib/agent-hive-lane";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

const SWARM_STROKE: Record<"scout" | "eval" | "sim" | "action", string> = {
  scout: "#00E5FF",
  eval: "#FFB800",
  sim: "#FF00AA",
  action: "#00FF88",
};

const AMBER_STROKE = "#FFB800";

const DEFAULT_STROKE_WIDTH = 10;
const FILL_HEX = "#141424";
/** Geometry in SVG user space — card scales via ``viewBox`` to match ``.qs-hex``. */
const VIEWBOX_SIZE = 140;

const STATUS_COLORS: Record<"live" | "idle" | "paused" | "error", string> = {
  live: "#00FF88",
  idle: "#FFB800",
  paused: "#FF3366",
  error: "#FF3366",
};

/** Public helper — ``unassigned`` when not in a hydrated swarm column. */
export function swarmKeyFromAgent(agent: AgentRow): keyof typeof SWARM_STROKE | "unassigned" {
  const lane = agentHiveLane(agent);
  if (lane === "unassigned" || lane === "queen") {
    return "unassigned";
  }
  return lane;
}

function statusVisual(status: string): { tone: keyof typeof STATUS_COLORS; pulse: boolean } {
  const u = status.toUpperCase();
  if (u === "RUNNING" || u === "BUSY") {
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
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
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

function flatTopHexVertices(cx: number, cy: number, radius: number): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    pts.push([cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)]);
  }
  return pts;
}

function roundedHexPath(pts: [number, number][], cornerR: number): string {
  const n = pts.length;
  let d = "";
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
    const r1 = Math.min(cornerR, len1 / 2 - 0.02);
    const r2 = Math.min(cornerR, len2 / 2 - 0.02);
    const p1: [number, number] = [curr[0] + (dx1 / len1) * r1, curr[1] + (dy1 / len1) * r1];
    const p2: [number, number] = [curr[0] + (dx2 / len2) * r2, curr[1] + (dy2 / len2) * r2];
    if (i === 0) {
      d += `M ${p1[0].toFixed(3)} ${p1[1].toFixed(3)} `;
    } else {
      d += `L ${p1[0].toFixed(3)} ${p1[1].toFixed(3)} `;
    }
    d += `Q ${curr[0].toFixed(3)} ${curr[1].toFixed(3)} ${p2[0].toFixed(3)} ${p2[1].toFixed(3)} `;
  }
  return `${d}Z`;
}

function buildHexPathD(size: number, strokeWidth: number): string {
  const cx = size / 2;
  const cy = size / 2;
  const r = Math.max(size / 2 - strokeWidth / 2 - 2, 8);
  const cornerR = Math.min(r * 0.07, r * 0.18);
  const pts = flatTopHexVertices(cx, cy, r);
  return roundedHexPath(pts, cornerR);
}

function laneToStroke(lane: AgentHiveLane): string {
  if (lane === "unassigned" || lane === "queen") {
    return AMBER_STROKE;
  }
  return SWARM_STROKE[lane];
}

interface HexAgentCardProps {
  agent: AgentRow;
  onClick?: () => void;
  href?: string;
  showPerformance?: boolean;
  renderAsDiv?: boolean;
  className?: string;
  /** Optional square pixel size override. */
  size?: number;
}

/**
 * Agent roster hex — SVG rounded stroke (~7% corner radius), pollen accent by lane.
 */
export function HexAgentCard({
  agent,
  onClick,
  href,
  showPerformance = false,
  renderAsDiv = false,
  className,
  size,
}: HexAgentCardProps): JSX.Element {
  const strokeW = DEFAULT_STROKE_WIDTH;
  const pathD = useMemo(() => buildHexPathD(VIEWBOX_SIZE, strokeW), [strokeW]);

  const lane = agentHiveLane(agent);
  const borderColor = laneToStroke(lane);
  const sk = swarmKeyFromAgent(agent);
  const pollenAccent = sk === "unassigned" ? AMBER_STROKE : SWARM_STROKE[sk];

  const sv = statusVisual(agent.status ?? "");
  const statusColor = STATUS_COLORS[sv.tone];
  const pollenVal = pollenDisplay(agent.pollen_points ?? 0);
  const scoreP = pctScore(agent.performance_score);
  const idle = agent.status.toUpperCase() === "IDLE";

  const glowStyle = sv.pulse ? { filter: `drop-shadow(0 0 14px ${borderColor}66)` } : undefined;

  const inner = (
    <>
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
        preserveAspectRatio="xMidYMid meet"
        style={glowStyle}
        aria-hidden
      >
        <path
          d={pathD}
          fill={FILL_HEX}
          stroke={borderColor}
          strokeWidth={strokeW}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      <div className="qs-hex__inner">
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

  const rootClass = cn("qs-hex group", idle && "opacity-[0.97]", className);
  const rootStyle: CSSProperties | undefined =
    size !== undefined ? { width: size, height: size } : undefined;

  if (href) {
    return (
      <Link href={href} prefetch={false} className={rootClass} style={rootStyle}>
        {inner}
      </Link>
    );
  }

  if (renderAsDiv) {
    return (
      <div className={rootClass} style={rootStyle}>
        {inner}
      </div>
    );
  }

  return (
    <button type="button" className={rootClass} style={rootStyle} onClick={onClick}>
      {inner}
    </button>
  );
}
