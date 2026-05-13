/**
 * Derived hive placement from API fields (frontend-only — no swarm reassignment).
 * An agent is listed under a swarm column only when anchored by swarm FK *and*
 * purpose/name hydrate the colony lane; bare FK counts as unassigned for UX.
 */

import type { AgentRow } from "@/lib/hive-types";

/** Tab filter for the live roster (no ``queen`` lane tab — queen visible under ``all``). */
export type AgentsSwarmFilter = "all" | "unassigned" | "scout" | "eval" | "sim" | "action";

/** Placement derived from DB (``swarm_id`` / optional ``sub_swarm_id``) + swarm metadata + queen tier. */
export type AgentHiveLane = "queen" | "unassigned" | "scout" | "eval" | "sim" | "action";

export function isQueenAgent(agent: AgentRow): boolean {
  const tier = (agent.hive_tier ?? "").toLowerCase();
  return tier === "orchestrator" || agent.name.toLowerCase() === "orchestrator";
}

/** Map API ``SwarmPurpose`` (and swarm name hints) to dashboard lanes. */
export function purposeToLane(purpose: string | null | undefined): "scout" | "eval" | "sim" | "action" | null {
  const u = (purpose ?? "").toLowerCase();
  if (u === "scout") {
    return "scout";
  }
  if (u === "eval") {
    return "eval";
  }
  if (u === "simulation") {
    return "sim";
  }
  if (u === "action") {
    return "action";
  }
  return null;
}

/** True when Postgres row references a swarm (``swarm_id`` or dashboard ``sub_swarm_id`` if present). */
export function hiveSwarmAnchored(agent: AgentRow): boolean {
  const sub = (agent as { sub_swarm_id?: string | null }).sub_swarm_id;
  const filled = (v: unknown): boolean => v !== undefined && v !== null && String(v).trim() !== "";
  return filled(agent.swarm_id) || filled(sub);
}

export function agentHiveLane(agent: AgentRow): AgentHiveLane {
  if (isQueenAgent(agent)) {
    return "queen";
  }
  if (!hiveSwarmAnchored(agent)) {
    return "unassigned";
  }
  const lane = purposeToLane(agent.swarm_purpose);
  if (lane) {
    return lane;
  }
  const label = (agent.swarm_name ?? "").toLowerCase();
  if (label.includes("scout")) {
    return "scout";
  }
  if (label.includes("eval")) {
    return "eval";
  }
  if (label.includes("sim")) {
    return "sim";
  }
  if (label.includes("action")) {
    return "action";
  }
  /** FK without join metadata — show as unassigned until manager assigns hydrated swarm. */
  return "unassigned";
}
