/** Opinionated swarm wizard templates — Phase 0 product entry points. */

export type SwarmWizardTemplateId = "exec-assistant" | "lead-waterfall" | "content-flywheel";

export interface SwarmWizardAgentSpec {
  name: string;
  hiveTier: "manager" | "worker";
  systemPrompt: string;
  tools: string[];
  scheduleType?: "on_demand" | "cron";
  scheduleValue?: string;
}

export interface SwarmWizardTemplate {
  id: SwarmWizardTemplateId;
  name: string;
  tagline: string;
  description: string;
  swarmName: string;
  swarmPurpose: "scout" | "eval" | "simulation" | "action";
  estimatedMinutes: number;
  timeSavedHoursPerWeek: number;
  /** Hex accent stored in swarm local_memory.hive_ui */
  accentHex: string;
  agents: SwarmWizardAgentSpec[];
  routine?: {
    name: string;
    goalTemplate: string;
    scheduleKind: "interval" | "cron";
    intervalSeconds?: number;
    cronExpr?: string;
  };
  comingSoon?: boolean;
}

export const SWARM_WIZARD_TEMPLATES: SwarmWizardTemplate[] = [
  {
    id: "exec-assistant",
    name: "Exec Assistant",
    tagline: "Personal chief-of-staff swarm in ~10 minutes",
    description:
      "Creates a colony with briefing, inbox triage, and calendar prep bees plus a morning supervisor routine.",
    swarmName: "Exec Assistant",
    swarmPurpose: "scout",
    estimatedMinutes: 10,
    timeSavedHoursPerWeek: 8,
    accentHex: "#FFB800",
    agents: [
      {
        name: "Briefing Manager",
        hiveTier: "manager",
        systemPrompt:
          "You are an executive briefing manager. Summarize priorities, deadlines, and risks from hive memory. Output verified briefings only.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Inbox Triage Bee",
        hiveTier: "worker",
        systemPrompt:
          "Triage incoming items: classify urgency, draft replies, and flag items needing human approval.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Calendar Prep Bee",
        hiveTier: "worker",
        systemPrompt:
          "Prepare meeting context Packs: attendees, open tasks, and suggested talking points.",
        tools: ["hive_memory_search", "task_list"],
      },
    ],
    routine: {
      name: "Morning executive briefing",
      goalTemplate:
        "Produce a verified morning briefing: top 3 priorities, calendar highlights, and blocked items needing approval.",
      scheduleKind: "cron",
      cronExpr: "0 7 * * 1-5",
    },
  },
  {
    id: "lead-waterfall",
    name: "Lead Waterfall",
    tagline: "Scrape → qualify → outreach for agencies and SMB sales",
    description:
      "Creates a sales colony with pipeline manager, lead scout, and outreach draft bees plus a daily waterfall review routine.",
    swarmName: "Lead Waterfall",
    swarmPurpose: "action",
    estimatedMinutes: 12,
    timeSavedHoursPerWeek: 12,
    accentHex: "#00FFFF",
    agents: [
      {
        name: "Pipeline Manager",
        hiveTier: "manager",
        systemPrompt:
          "You are a sales pipeline manager. Score leads by fit and urgency, advance waterfall stages, and surface only verified next actions.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Lead Scout Bee",
        hiveTier: "worker",
        systemPrompt:
          "Discover and enrich inbound leads from hive memory and forager feeds. Normalize company, role, and intent signals before handoff.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Outreach Draft Bee",
        hiveTier: "worker",
        systemPrompt:
          "Qualify leads against ICP criteria, draft personalized outreach, and flag messages that require human approval before send.",
        tools: ["hive_memory_search", "task_list"],
      },
    ],
    routine: {
      name: "Daily pipeline waterfall",
      goalTemplate:
        "Run the lead waterfall: new leads scraped, qualified with scores, top 5 outreach drafts ready for approval, stale leads flagged.",
      scheduleKind: "cron",
      cronExpr: "0 8 * * 1-5",
    },
  },
  {
    id: "content-flywheel",
    name: "Content Flywheel",
    tagline: "Research → draft → social with simulation gate",
    description:
      "Creates a content colony with editor manager, topic research, and draft bees plus a recurring flywheel routine before publish.",
    swarmName: "Content Flywheel",
    swarmPurpose: "scout",
    estimatedMinutes: 12,
    timeSavedHoursPerWeek: 10,
    accentHex: "#FF00AA",
    agents: [
      {
        name: "Content Editor Manager",
        hiveTier: "manager",
        systemPrompt:
          "You are a content editor manager. Prioritize topics, enforce brand voice, and release only simulation-verified drafts to outputs.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Topic Research Bee",
        hiveTier: "worker",
        systemPrompt:
          "Research trending topics and source clusters from hive memory and forager feeds. Return cited briefs with confidence scores.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Draft & Social Bee",
        hiveTier: "worker",
        systemPrompt:
          "Turn research briefs into long-form drafts and social snippets. Run simulation checks and queue publish-ready packs for human approval.",
        tools: ["hive_memory_search", "task_list"],
      },
    ],
    routine: {
      name: "Content flywheel cycle",
      goalTemplate:
        "Run the content flywheel: 3 researched topics, 1 verified long-form draft, 5 social snippets staged for approval, archive prior winners to outputs.",
      scheduleKind: "cron",
      cronExpr: "0 9 * * 1,3,5",
    },
  },
];

export function getSwarmWizardTemplate(id: string): SwarmWizardTemplate | undefined {
  return SWARM_WIZARD_TEMPLATES.find((t) => t.id === id);
}

/** Free commercial tier caps — keep in sync with billing.py PlanDefinition. */
export const COMMERCIAL_FREE_MAX_AGENTS = 2;
export const COMMERCIAL_FREE_MAX_SWARMS = 1;

/** True when template exceeds commercial Free limits (Pro required). */
export function templateRequiresProTier(
  template: SwarmWizardTemplate,
  platformMode: string,
  subscriptionTier: string,
): boolean {
  if (platformMode !== "commercial") {
    return false;
  }
  const tier = subscriptionTier.trim().toLowerCase();
  if (tier === "pro" || tier === "enterprise") {
    return false;
  }
  return (
    template.agents.length > COMMERCIAL_FREE_MAX_AGENTS || COMMERCIAL_FREE_MAX_SWARMS < 1
  );
}
