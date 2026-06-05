/** Opinionated swarm wizard templates — Virtual Company departments + personal colonies. */

import {
  DEPARTMENT_EXECUTION_TOOLS,
  executionPromptSuffix,
} from "@/lib/virtual-company-departments";

export type SwarmWizardTemplateId =
  | "marketing-ops"
  | "lead-waterfall"
  | "finance-ops"
  | "digital-ops"
  | "eshop-ops"
  | "rnd-dev"
  | "product-ship"
  | "sentinel-radar"
  | "exec-assistant"
  | "content-flywheel"
  | "content-flywheel-v2"
  | "polymarket-trading"
  | "polymarket-prediction-evaluator"
  | "trading-content-hybrid"
  | "life-business-os"
  | "faceless-media-agency"
  | "micro-saas-factory"
  | "life-os";

export type SwarmWizardTemplateCategory = "virtual_company" | "sentinel" | "personal";

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
  category: SwarmWizardTemplateCategory;
  swarmName: string;
  swarmPurpose: "scout" | "eval" | "simulation" | "action";
  estimatedMinutes: number;
  timeSavedHoursPerWeek: number;
  accentHex: string;
  agents: SwarmWizardAgentSpec[];
  routine?: {
    name: string;
    goalTemplate: string;
    scheduleKind: "interval" | "cron";
    intervalSeconds?: number;
    cronExpr?: string;
  };
  prdKanban?: {
    kanbanHint: string;
  };
  comingSoon?: boolean;
}

const EXEC = executionPromptSuffix();
const DEPT_TOOLS = [...DEPARTMENT_EXECUTION_TOOLS];

export const SWARM_WIZARD_TEMPLATES: SwarmWizardTemplate[] = [
  {
    id: "marketing-ops",
    name: "Marketing Ops",
    tagline: "Research → content → simulate publish (free OAuth)",
    description:
      "Virtual Company marketing department: campaign briefs, drafts, and publish packs via Execution Studio (Notion + Gmail). Default simulate — zero ad API cost.",
    category: "virtual_company",
    swarmName: "Marketing Ops",
    swarmPurpose: "action",
    estimatedMinutes: 12,
    timeSavedHoursPerWeek: 12,
    accentHex: "#FF00AA",
    agents: [
      {
        name: "Marketing Manager",
        hiveTier: "manager",
        systemPrompt:
          `You are the marketing department manager. Plan campaigns per firm_id, enforce brand voice, route publish through simulate-first queue. Use multi-tenant-content-calendar skill.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Topic Research Bee",
        hiveTier: "worker",
        systemPrompt:
          `Research topics from HiveMind and forager feeds. Store cited briefs in Notion via mcp_invoke when connector is active.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Content Draft Bee",
        hiveTier: "worker",
        systemPrompt:
          `Turn briefs into blog posts and social snippets. Simulation-gate all outputs before handoff to publish.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Calendar Orchestrator Bee",
        hiveTier: "worker",
        systemPrompt:
          `Maintain per-firm content calendars in Notion. Tag every row with firm_id — never cross-mix brands.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Publish Pack Bee",
        hiveTier: "worker",
        systemPrompt:
          `Stage publish-ready packs in Notion and Gmail drafts via mcp_invoke. Never live-send without operator approval.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Marketing ops cycle",
      goalTemplate:
        "Run marketing ops for each active firm_id: 3 researched topics, 1 verified long-form draft, 5 social snippets in Notion simulate mode, calendar updated, Gmail drafts staged for approval.",
      scheduleKind: "cron",
      cronExpr: "0 9 * * 1,3,5",
    },
  },
  {
    id: "eshop-ops",
    name: "E-shop Ops",
    tagline: "Research → listings → orders → Stripe webhooks",
    description:
      "Full e-commerce ops swarm: competitor scrape, Shopify catalog/order sync, Stripe Checkout simulate-first, Apify intel. Financial mutations require operator approval.",
    category: "virtual_company",
    swarmName: "E-shop Ops",
    swarmPurpose: "action",
    estimatedMinutes: 14,
    timeSavedHoursPerWeek: 14,
    accentHex: "#00E5FF",
    agents: [
      {
        name: "E-shop Manager",
        hiveTier: "manager",
        systemPrompt:
          `Supervise e-shop ops across one or more storefronts. Default simulate; live Shopify/Stripe only after real-money-risk-gate approval.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Product Research Bee",
        hiveTier: "worker",
        systemPrompt:
          `Competitor scrape + pricing intel via Apify and browser harness. Store verified briefs in Notion and HiveMind.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Listing Writer Bee",
        hiveTier: "worker",
        systemPrompt:
          `Draft SEO listings and A/B copy variants. Stage in Notion; sync to Shopify products_list simulate mode only.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Order Monitor Bee",
        hiveTier: "worker",
        systemPrompt:
          `Poll Shopify orders_list; correlate with Stripe webhook events. Flag anomalies for operator review — never refund without approval.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "E-shop ops tick",
      goalTemplate:
        "E-shop ops: competitor brief, 2 listing drafts, orders snapshot from Shopify, payment events summary from webhook queue (simulate).",
      scheduleKind: "cron",
      cronExpr: "0 11 * * 1-5",
    },
  },
  {
    id: "lead-waterfall",
    name: "Sales Ops",
    tagline: "Pipeline → qualify → outreach drafts (approval before send)",
    description:
      "Virtual Company sales department: lead waterfall with Gmail/Notion execution lane. Simulate outreach until operator approves live send.",
    category: "virtual_company",
    swarmName: "Sales Ops",
    swarmPurpose: "action",
    estimatedMinutes: 12,
    timeSavedHoursPerWeek: 12,
    accentHex: "#00FFFF",
    agents: [
      {
        name: "Pipeline Manager",
        hiveTier: "manager",
        systemPrompt:
          `You are the sales pipeline manager. Score leads, advance stages, surface verified next actions only.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Lead Scout Bee",
        hiveTier: "worker",
        systemPrompt:
          `Discover and enrich leads from HiveMind and forager feeds. Log pipeline rows to Notion when connector active.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Outreach Draft Bee",
        hiveTier: "worker",
        systemPrompt:
          `Draft personalized outreach in Gmail simulate mode. Flag every send for human approval before live.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Daily sales waterfall",
      goalTemplate:
        "Run sales waterfall: qualify leads, top 5 outreach drafts in Gmail simulate mode, stale leads flagged in Notion.",
      scheduleKind: "cron",
      cronExpr: "0 8 * * 1-5",
    },
  },
  {
    id: "finance-ops",
    name: "Finance Ops",
    tagline: "Read-only reports — no live banking APIs",
    description:
      "Virtual Company finance department: cashflow summaries and budget reports from HiveMind into Notion. Read-only — never move money via API.",
    category: "virtual_company",
    swarmName: "Finance Ops",
    swarmPurpose: "scout",
    estimatedMinutes: 10,
    timeSavedHoursPerWeek: 6,
    accentHex: "#FFB800",
    agents: [
      {
        name: "Finance Manager",
        hiveTier: "manager",
        systemPrompt:
          `You are the finance controller. Produce read-only reports, flag anomalies, never initiate payments or banking API writes.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Ledger Summary Bee",
        hiveTier: "worker",
        systemPrompt:
          `Aggregate figures from HiveMind notes and operator uploads. Output structured summaries with confidence scores.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Report Pack Bee",
        hiveTier: "worker",
        systemPrompt:
          `Write monthly finance report pages to Notion via mcp_invoke (simulate default). Export PDF links only after verification.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Weekly finance snapshot",
      goalTemplate:
        "Produce verified weekly finance snapshot: cashflow summary, budget variance notes, anomalies — Notion simulate write.",
      scheduleKind: "cron",
      cronExpr: "0 7 * * 1",
    },
  },
  {
    id: "digital-ops",
    name: "Digital Ops",
    tagline: "UX research & conversion ideas — hive-first, free",
    description:
      "Virtual Company e-commerce/digital department: research, UX audit notes, and conversion hypotheses stored in Notion. No paid analytics API required.",
    category: "virtual_company",
    swarmName: "Digital Ops",
    swarmPurpose: "scout",
    estimatedMinutes: 11,
    timeSavedHoursPerWeek: 8,
    accentHex: "#00E5FF",
    agents: [
      {
        name: "Digital Manager",
        hiveTier: "manager",
        systemPrompt:
          `You are the digital/e-commerce manager. Prioritize UX and conversion experiments with verified research only.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "UX Research Bee",
        hiveTier: "worker",
        systemPrompt:
          `Audit flows from HiveMind context and public pages. Document findings with evidence — browser harness only when domain allowlisted.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Conversion Ideas Bee",
        hiveTier: "worker",
        systemPrompt:
          `Propose A/B test ideas and landing improvements. Store experiment backlog in Notion simulate mode.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Digital ops review",
      goalTemplate:
        "Digital ops review: 3 UX findings, 2 conversion hypotheses, experiment backlog updated in Notion (simulate).",
      scheduleKind: "cron",
      cronExpr: "0 10 * * 2",
    },
  },
  {
    id: "rnd-dev",
    name: "R&D / Development",
    tagline: "GitHub PR lane + opportunity research",
    description:
      "Virtual Company R&D: codebase health via Queen Maintainer handoff, GitHub issues/PRs, and mini-app opportunity notes in HiveMind.",
    category: "virtual_company",
    swarmName: "R&D Development",
    swarmPurpose: "action",
    estimatedMinutes: 14,
    timeSavedHoursPerWeek: 10,
    accentHex: "#00FF88",
    agents: [
      {
        name: "R&D Manager",
        hiveTier: "manager",
        systemPrompt:
          `You are R&D lead. Route codebase changes through Queen Maintainer PR proposals only — never commit to main.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Codebase Scout Bee",
        hiveTier: "worker",
        systemPrompt:
          `Inspect repo health signals and open GitHub issues/PR drafts via mcp_invoke when github_rest connector active. PR-only workflow.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Opportunity Research Bee",
        hiveTier: "worker",
        systemPrompt:
          `Research mini-app and tooling opportunities from HiveMind and forager feeds. Store ranked ideas with effort estimates.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "R&D weekly scan",
      goalTemplate:
        "R&D scan: tech debt notes, top 3 mini-app opportunities, GitHub issue drafts (simulate) for operator review.",
      scheduleKind: "cron",
      cronExpr: "0 11 * * 3",
    },
  },
  {
    id: "product-ship",
    name: "Product Ship",
    tagline: "PRD → slices → GitHub/Notion ship lane",
    description:
      "Virtual Company product department: PRD planner, tracer bullets, Kanban slices, and Notion/GitHub execution via Execution Studio.",
    category: "virtual_company",
    swarmName: "Product Ship",
    swarmPurpose: "action",
    estimatedMinutes: 15,
    timeSavedHoursPerWeek: 14,
    accentHex: "#9966FF",
    prdKanban: {
      kanbanHint: "After intake, Auto Workflow Breaker creates vertical slices on /tasks and /workflows.",
    },
    agents: [
      {
        name: "PRD Planner Manager",
        hiveTier: "manager",
        systemPrompt:
          `You are product manager. Turn requests into PRDs with success criteria and vertical slices. Sync roadmap pages to Notion simulate mode.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Tracer Bullet Bee",
        hiveTier: "worker",
        systemPrompt:
          `Decompose PRD slices into 3–7 workflow steps with guardrails and evaluation criteria.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Kanban Slice Bee",
        hiveTier: "worker",
        systemPrompt:
          `Materialize workflow steps as Kanban child tasks. Preserve parent/child lineage for review.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Ship Gate Bee",
        hiveTier: "worker",
        systemPrompt:
          `Run simulation and TDD checks. Link shipped slices to GitHub via mcp_invoke when connector active.${EXEC}`,
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Weekly ship review",
      goalTemplate:
        "Product ship review: completed slices, blocked items, Notion roadmap update (simulate), next slice for approval.",
      scheduleKind: "cron",
      cronExpr: "0 16 * * 5",
    },
  },
  {
    id: "sentinel-radar",
    name: "Sentinel Radar",
    tagline: "World signals · trends · opportunities (read-only, €0)",
    description:
      "Always-on intelligence colony: geopolitics, industry trends, and mini-app opportunities into HiveMind. Read-only — no external API spend.",
    category: "sentinel",
    swarmName: "Sentinel Radar",
    swarmPurpose: "scout",
    estimatedMinutes: 8,
    timeSavedHoursPerWeek: 5,
    accentHex: "#66CCFF",
    agents: [
      {
        name: "Sentinel Manager",
        hiveTier: "manager",
        systemPrompt:
          "You are the sentinel manager. Coordinate read-only scans; store verified signals in HiveMind with tags. Never execute live external writes.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "World Signals Bee",
        hiveTier: "worker",
        systemPrompt:
          "Scan geopolitical and macro signals relevant to operator focus areas. Cite sources; confidence scores required.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Trend Radar Bee",
        hiveTier: "worker",
        systemPrompt:
          "Track industry and technology trends from HiveMind and forager feeds. Tag entries trend-radar.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Opportunity Scout Bee",
        hiveTier: "worker",
        systemPrompt:
          "Identify mini-app, SaaS, and automation opportunities with effort estimates. Tag opportunities.",
        tools: ["hive_memory_search", "task_list"],
      },
    ],
    routine: {
      name: "Daily sentinel scan",
      goalTemplate:
        "Sentinel scan: top world signals, 5 industry trends, 3 ranked opportunities — all verified, HiveMind only.",
      scheduleKind: "cron",
      cronExpr: "0 6 * * *",
    },
  },
  {
    id: "exec-assistant",
    name: "Exec Assistant",
    tagline: "Personal chief-of-staff swarm in ~10 minutes",
    description:
      "Personal colony with briefing, inbox triage, and calendar prep bees plus a morning supervisor routine.",
    category: "personal",
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
          "Prepare meeting context packs: attendees, open tasks, and suggested talking points.",
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
    id: "content-flywheel-v2",
    name: "Content Flywheel 2.0",
    tagline: "Research → recipe match → critic → hooks → performance loop",
    description:
      "Marketing swarm wired to Recipe Library cosine match, hook variants, and Publish Performance insights — simulate-first publish lane.",
    category: "virtual_company",
    swarmName: "Content Flywheel 2.0",
    swarmPurpose: "action",
    estimatedMinutes: 14,
    timeSavedHoursPerWeek: 14,
    accentHex: "#00FFFF",
    agents: [
      {
        name: "Flywheel Manager",
        hiveTier: "manager",
        systemPrompt:
          `Orchestrate content flywheel: research → recipe match (≥0.85) → draft → critic → publish pack. Use Publish Performance insights for next iteration.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Research Forager Bee",
        hiveTier: "worker",
        systemPrompt:
          "Gather cited research from HiveMind and foragers. Output structured briefs — no raw dumps.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Recipe Matcher Bee",
        hiveTier: "worker",
        systemPrompt:
          "Match task to verified recipes via cosine ≥0.85. Prefer imitation top performers when available.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Hook Optimizer Bee",
        hiveTier: "worker",
        systemPrompt:
          "Generate hook variants for publish packs. Track winners via Publish Performance channel stats.",
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Content flywheel cycle",
      goalTemplate:
        "Run flywheel: 2 researched topics, 1 recipe match, 1 verified publish pack with hook variants, simulate-only.",
      scheduleKind: "cron",
      cronExpr: "0 10 * * 1,3,5",
    },
  },
  {
    id: "polymarket-prediction-evaluator",
    name: "Polymarket Prediction Evaluator",
    tagline: "Research + consensus only — no orders",
    description:
      "Evaluation-only swarm: scan Polymarket markets, 3-model consensus, edge scoring. Never places orders — hand off to live executor after operator approval.",
    category: "personal",
    swarmName: "Polymarket Evaluator",
    swarmPurpose: "scout",
    estimatedMinutes: 8,
    timeSavedHoursPerWeek: 6,
    accentHex: "#00FFFF",
    comingSoon: false,
    agents: [
      {
        name: "Evaluator Supervisor",
        hiveTier: "manager",
        systemPrompt:
          `Supervise Polymarket evaluation only — no execute_trade, no CLOB orders. Rank markets by edge vs price.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Market Scanner Bee",
        hiveTier: "worker",
        systemPrompt:
          "Fetch Polymarket Gamma markets/events. Filter liquidity, time-to-resolution, and category fit.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Consensus Analyst Bee",
        hiveTier: "worker",
        systemPrompt:
          "Run 3-lane analysis consensus. Output probability estimate, confidence, and edge vs market price.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Edge Critic Bee",
        hiveTier: "worker",
        systemPrompt:
          "Challenge consensus — flag thin liquidity, resolution risk, and overconfidence. No trade recommendations without caveats.",
        tools: [],
      },
    ],
    routine: {
      name: "Market evaluation sweep",
      goalTemplate:
        "Scan Polymarket, run consensus on top 5 markets, deliver ranked evaluation report — no orders.",
      scheduleKind: "cron",
      cronExpr: "0 8,14 * * 1-5",
    },
  },
  {
    id: "polymarket-trading",
    name: "Polymarket Live Executor",
    tagline: "Real USDC orders — after evaluator + risk gate",
    description:
      "Live trading swarm for Polymarket: consumes evaluator reports, passes risk validator, places signed CLOB orders when operator approves.",
    category: "personal",
    swarmName: "Polymarket Live Executor",
    swarmPurpose: "action",
    estimatedMinutes: 10,
    timeSavedHoursPerWeek: 8,
    accentHex: "#FFB800",
    comingSoon: false,
    agents: [
      {
        name: "Live Trading Supervisor",
        hiveTier: "manager",
        systemPrompt:
          `Supervise Polymarket LIVE lane only — real USDC. Require evaluator report + human approval per order unless trusted_auto.${EXEC}`,
        tools: DEPT_TOOLS,
      },
      {
        name: "Risk Validator Bee",
        hiveTier: "worker",
        systemPrompt:
          "Validate every order: max order USD, daily loss, confidence threshold, live flag. Block and audit when checks fail.",
        tools: [],
      },
      {
        name: "CLOB Executor Bee",
        hiveTier: "worker",
        systemPrompt:
          "Place signed Polymarket CLOB orders via external project API only after risk pass and operator approval.",
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Live execution cycle",
      goalTemplate:
        "Review latest evaluator report, risk-gate approved markets, request operator approval for live orders.",
      scheduleKind: "cron",
      cronExpr: "0 9,15 * * 1-5",
    },
  },
  {
    id: "content-flywheel",
    name: "Content Flywheel (legacy)",
    tagline: "Use Marketing Ops for Execution Studio wiring",
    description: "Legacy template — prefer Marketing Ops for department swarm with mcp_invoke execution lane.",
    category: "personal",
    swarmName: "Content Flywheel",
    swarmPurpose: "scout",
    estimatedMinutes: 12,
    timeSavedHoursPerWeek: 10,
    accentHex: "#FF6699",
    comingSoon: true,
    agents: [],
  },
  {
    id: "life-os",
    name: "Life OS",
    tagline: "Dump folder before sleep → morning priorities",
    description:
      "Overnight colony: ingest dump, graphify knowledge, extract tasks, deliver verified morning briefing.",
    category: "personal",
    swarmName: "Life OS",
    swarmPurpose: "scout",
    estimatedMinutes: 8,
    timeSavedHoursPerWeek: 15,
    accentHex: "#00FF88",
    comingSoon: false,
    agents: [
      {
        name: "Overnight Supervisor",
        hiveTier: "manager",
        systemPrompt:
          "You are an overnight life-OS supervisor. Triage dumps, prioritize stalled projects, produce verified morning briefing only.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Dump Ingest Bee",
        hiveTier: "worker",
        systemPrompt:
          "Ingest folder files and voice notes into hive memory. Classify by project, urgency, and staleness.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Task Extractor Bee",
        hiveTier: "worker",
        systemPrompt:
          "Extract actionable tasks from overnight ingest. Link to graph nodes, dedupe, queue approval items.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Morning Brief Bee",
        hiveTier: "worker",
        systemPrompt:
          "Compile morning summary: priorities, stalled projects, pollen earned, suggested next actions.",
        tools: ["hive_memory_search", "task_list"],
      },
    ],
    routine: {
      name: "Overnight dump & dream cycle",
      goalTemplate:
        "Process overnight dump: graphify ingest, extract tasks, simulate outputs, deliver morning briefing.",
      scheduleKind: "cron",
      cronExpr: "0 6 * * *",
    },
  },
  {
    id: "trading-content-hybrid",
    name: "Trading + Content Hybrid",
    tagline: "Deprecated — use Polymarket evaluator + executor",
    description:
      "Removed — paper trading and trade→content flywheel deprecated. Use polymarket-prediction-evaluator and polymarket-trading templates.",
    category: "personal",
    swarmName: "Trading Content Hybrid",
    swarmPurpose: "action",
    estimatedMinutes: 14,
    timeSavedHoursPerWeek: 18,
    accentHex: "#FFB800",
    comingSoon: true,
    agents: [
      {
        name: "Hybrid Supervisor",
        hiveTier: "manager",
        systemPrompt:
          "Coordinate paper Polymarket trading and content publish lanes. Never skip simulate or risk gate.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Market Forager Bee",
        hiveTier: "worker",
        systemPrompt: "Scan Polymarket via Gamma connector. Rank opportunities with Analysis Swarm consensus.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Risk Gate Bee",
        hiveTier: "worker",
        systemPrompt: "Validate every trade against confidence, daily loss, and max order guardrails.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Trade→Content Bee",
        hiveTier: "worker",
        systemPrompt: "After verified paper fill, draft simulate-only publish pack with hook variants.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Publish Ops Bee",
        hiveTier: "worker",
        systemPrompt: "Queue approved packs, run social simulate, escalate to live only after operator review.",
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Hybrid tick + content cycle",
      goalTemplate:
        "Paper tick: forage, consensus, risk gate, fill if allowed, draft content, simulate publish.",
      scheduleKind: "cron",
      cronExpr: "0 */4 * * 1-5",
    },
  },
  {
    id: "life-business-os",
    name: "Life + Business OS",
    tagline: "Morning brief + trading/content lanes in one colony",
    description:
      "Bundle Life OS overnight dump with morning brief — personal priorities (no paper trading lane).",
    category: "personal",
    swarmName: "Life Business OS",
    swarmPurpose: "scout",
    estimatedMinutes: 16,
    timeSavedHoursPerWeek: 22,
    accentHex: "#00FF88",
    comingSoon: false,
    agents: [
      {
        name: "Life-Business Supervisor",
        hiveTier: "manager",
        systemPrompt:
          "Merge morning Life OS priorities with trading/content hybrid actions. Surface top 3 verified next steps.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Overnight Dump Bee",
        hiveTier: "worker",
        systemPrompt: "Ingest dump folder, graphify, extract tasks for morning brief.",
        tools: ["hive_memory_search"],
      },
      {
        name: "Morning Brief Bee",
        hiveTier: "worker",
        systemPrompt: "Deliver verified morning briefing with stalled projects and pollen earned.",
        tools: ["hive_memory_search", "task_list"],
      },
    ],
    routine: {
      name: "Overnight + hybrid morning cycle",
      goalTemplate:
        "Overnight dump → morning brief → top 3 personal priorities.",
      scheduleKind: "cron",
      cronExpr: "0 6 * * *",
    },
  },
  {
    id: "faceless-media-agency",
    name: "Faceless Media Agency",
    tagline: "White-label publish lane for 3 client slots",
    description:
      "Agency colony: white-label brand, per-client publish lanes, simulate-first social, human approve live.",
    category: "virtual_company",
    swarmName: "Faceless Media Agency",
    swarmPurpose: "action",
    estimatedMinutes: 18,
    timeSavedHoursPerWeek: 25,
    accentHex: "#FF00AA",
    comingSoon: false,
    agents: [
      {
        name: "Agency Supervisor",
        hiveTier: "manager",
        systemPrompt:
          "Manage multi-client publish lanes. White-label output. Never live without simulate + human approve.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "Client Research Bee",
        hiveTier: "worker",
        systemPrompt: "Research client niche topics. Output structured briefs for content packs.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Content Pack Bee",
        hiveTier: "worker",
        systemPrompt: "Draft publish packs with hook variants per client channel. Simulate-only default.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Publish Ops Bee",
        hiveTier: "worker",
        systemPrompt: "Queue approved packs, run social simulate, escalate live only after operator review.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Performance Bee",
        hiveTier: "worker",
        systemPrompt: "Track publish performance per channel. Recommend hook winners for next cycle.",
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Agency weekly client cycle",
      goalTemplate:
        "Per client: research brief → publish pack → simulate → queue live approval.",
      scheduleKind: "cron",
      cronExpr: "0 9 * * 1",
    },
  },
  {
    id: "micro-saas-factory",
    name: "Micro-SaaS Factory",
    tagline: "Landing + auth + billing + deploy recipe",
    description:
      "Product factory colony: MVP scope, landing draft, JWT auth pattern, billing checklist, docker deploy recipe — all simulate-first.",
    category: "virtual_company",
    swarmName: "Micro-SaaS Factory",
    swarmPurpose: "action",
    estimatedMinutes: 20,
    timeSavedHoursPerWeek: 30,
    accentHex: "#00FFFF",
    comingSoon: false,
    agents: [
      {
        name: "Factory Supervisor",
        hiveTier: "manager",
        systemPrompt:
          "Orchestrate Micro-SaaS MVP factory lanes. Never skip simulate or human approve for deploy.",
        tools: ["hive_memory_search", "task_list"],
      },
      {
        name: "MVP Scope Bee",
        hiveTier: "worker",
        systemPrompt: "Define one-sharp-job MVP and decompose into 3–5 atomic bee workflows.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Landing Builder Bee",
        hiveTier: "worker",
        systemPrompt: "Draft public landing page copy and CTA for Swarm Builder magnet flow.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Auth Pattern Bee",
        hiveTier: "worker",
        systemPrompt: "Document JWT + tenant RBAC auth pattern for product users.",
        tools: DEPT_TOOLS,
      },
      {
        name: "Deploy Recipe Bee",
        hiveTier: "worker",
        systemPrompt: "Produce verified docker-compose deploy recipe with health-check gate.",
        tools: DEPT_TOOLS,
      },
    ],
    routine: {
      name: "Micro-SaaS factory cycle",
      goalTemplate:
        "Factory: MVP scope → landing → auth doc → billing checklist → deploy recipe (simulate).",
      scheduleKind: "cron",
      cronExpr: "0 14 * * 5",
    },
  },
];

export function getSwarmWizardTemplate(id: string): SwarmWizardTemplate | undefined {
  return SWARM_WIZARD_TEMPLATES.find((t) => t.id === id);
}

export function getBuildableSwarmTemplates(): SwarmWizardTemplate[] {
  return SWARM_WIZARD_TEMPLATES.filter((t) => !t.comingSoon && t.agents.length > 0);
}

export function getVirtualCompanyTemplates(): SwarmWizardTemplate[] {
  return getBuildableSwarmTemplates().filter((t) => t.category === "virtual_company");
}

export function getSentinelSwarmTemplates(): SwarmWizardTemplate[] {
  return getBuildableSwarmTemplates().filter((t) => t.category === "sentinel");
}

export function getPersonalSwarmTemplates(): SwarmWizardTemplate[] {
  return getBuildableSwarmTemplates().filter((t) => t.category === "personal");
}

export const COMMERCIAL_FREE_MAX_AGENTS = 2;
export const COMMERCIAL_FREE_MAX_SWARMS = 1;

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
