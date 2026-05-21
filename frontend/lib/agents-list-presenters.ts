import type { AgentsSwarmFilter, AgentHiveLane } from "@/lib/agent-hive-lane";
import { isQueenAgent } from "@/lib/agent-hive-lane";
import type { AgentRow } from "@/lib/hive-types";

function filledHiveId(value: unknown): boolean {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

function hasSubSwarmId(agent: AgentRow): boolean {
  return filledHiveId(agent.sub_swarm_id);
}

function rawSwarmHints(agent: AgentRow): string {
  const parts = [agent.swarm_type, agent.swarm?.name, agent.swarm_name, agent.swarm_purpose].filter(Boolean);
  return parts.join(" ").toLowerCase();
}

/** Roster grouping for swarm filter pills (workers only). */
export function workerSwarmPillBucket(agent: AgentRow): Exclude<AgentsSwarmFilter, "all"> {
  if (!hasSubSwarmId(agent)) {
    return "unassigned";
  }
  const raw = rawSwarmHints(agent);
  if (raw.includes("scout")) {
    return "scout";
  }
  if (raw.includes("eval")) {
    return "eval";
  }
  if (raw.includes("sim")) {
    return "sim";
  }
  if (raw.includes("action")) {
    return "action";
  }
  return "unassigned";
}

export function agentListLane(agent: AgentRow): AgentHiveLane {
  if (isQueenAgent(agent)) {
    return "queen";
  }
  const bucket = workerSwarmPillBucket(agent);
  if (bucket === "unassigned") {
    return "unassigned";
  }
  return bucket;
}

export function roleDisplayName(role: string): string {
  const r = role.toLowerCase();
  const map: Record<string, string> = {
    scraper: "ScraperBee",
    evaluator: "EvaluatorBee",
    simulator: "SimulatorBee",
    reporter: "ReporterBee",
    trader: "TraderBee",
    marketer: "MarketerBee",
    blog_writer: "BlogWriterBee",
    social_poster: "SocialPosterBee",
    learner: "LearnerBee",
    recipe_keeper: "RecipeKeeperBee",
  };
  if (map[r]) {
    return map[r];
  }
  const cleaned = r.replace(/_/g, " ");
  return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)}Bee`;
}

export function laneTabLabel(key: Exclude<AgentsSwarmFilter, "all">): string {
  const labels: Record<Exclude<AgentsSwarmFilter, "all">, string> = {
    unassigned: "Unassigned",
    scout: "Scout Swarm",
    eval: "Eval Swarm",
    sim: "Sim Swarm",
    action: "Action Swarm",
  };
  return labels[key];
}

export interface LaneTheme {
  hexBorder: string;
  barBg: string;
  glow: string;
  listBar: string;
  scoreText: string;
  pillClass: string;
}

export function laneTheme(lane: AgentHiveLane, agent: AgentRow): LaneTheme {
  if (lane === "queen") {
    return {
      hexBorder: "border-pollen/90",
      barBg: "bg-pollen",
      glow: "shadow-[0_0_26px_rgb(255_184_0/0.4)]",
      listBar: "bg-pollen",
      scoreText: "text-pollen",
      pillClass: "border-pollen/45 text-pollen",
    };
  }
  if (lane === "unassigned") {
    return {
      hexBorder: "border-pollen/65",
      barBg: "bg-pollen/85",
      glow: "shadow-[0_0_22px_rgb(255_184_0/0.33)]",
      listBar: "bg-pollen/80",
      scoreText: "text-pollen/90",
      pillClass: "border-pollen/35 text-pollen/90",
    };
  }
  const n = agent.name.toLowerCase();
  const orangeAction = lane === "action" && n.includes("action") && (agent.id.charCodeAt(0) ?? 0) % 2 === 1;
  if (lane === "scout") {
    return {
      hexBorder: "border-[#00E5FF]/85",
      barBg: "bg-[#00E5FF]",
      glow: "shadow-[0_0_24px_rgb(0_229_255/0.32)]",
      listBar: "bg-[#00E5FF]",
      scoreText: "text-[#00E5FF]",
      pillClass: "border-[#00E5FF]/45 text-[#00E5FF]",
    };
  }
  if (lane === "eval") {
    return {
      hexBorder: "border-pollen/80",
      barBg: "bg-pollen",
      glow: "shadow-[0_0_24px_rgb(255_184_0/0.28)]",
      listBar: "bg-pollen",
      scoreText: "text-pollen",
      pillClass: "border-pollen/45 text-pollen",
    };
  }
  if (lane === "sim") {
    return {
      hexBorder: "border-alert/80",
      barBg: "bg-alert",
      glow: "shadow-[0_0_24px_rgb(255_0_170/0.28)]",
      listBar: "bg-alert",
      scoreText: "text-alert",
      pillClass: "border-alert/45 text-alert",
    };
  }
  if (orangeAction) {
    return {
      hexBorder: "border-orange-400/85",
      barBg: "bg-orange-400",
      glow: "shadow-[0_0_22px_rgb(251_146_60/0.3)]",
      listBar: "bg-orange-400",
      scoreText: "text-orange-300",
      pillClass: "border-orange-400/50 text-orange-300",
    };
  }
  return {
    hexBorder: "border-success/80",
    barBg: "bg-success",
    glow: "shadow-[0_0_22px_rgb(0_255_136/0.28)]",
    listBar: "bg-success",
    scoreText: "text-success",
    pillClass: "border-success/45 text-success",
  };
}

export function shouldVirtualizeAgentList(agentCount: number, virtualizeList: boolean): boolean {
  return virtualizeList && agentCount > 0;
}
