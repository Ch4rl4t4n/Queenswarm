/** Automation Ladder — Brad / Claude 5-level framework mapped to Queenswarm primitives. */

import { MANUAL_HREFS } from "@/lib/manual-routes";

export interface AutomationLadderLevel {
  level: number;
  id: string;
  title: string;
  summary: string;
  whenToUse: string[];
  skipWhen: string[];
  queenswarmPath: string;
  href: string;
}

export const AUTOMATION_LADDER_LEVELS: AutomationLadderLevel[] = [
  {
    level: 1,
    id: "skills",
    title: "Skills & presets",
    summary: "Reusable prompt packs — run on demand when you click Create.",
    whenToUse: [
      "Same workflow weekly but inputs change",
      "You want Pattern Router preview before spawn",
      "Manual approve gate stays ON",
    ],
    skipWhen: ["You need it to run while you sleep", "Whole team depends on exact schedule"],
    queenswarmPath: "Session presets · Skill pack · Pattern Router preview",
    href: MANUAL_HREFS.agentsSessions,
  },
  {
    level: 2,
    id: "desktop",
    title: "Desktop / browser lane",
    summary: "Logged-in browser harness — your machine, your Chrome session.",
    whenToUse: [
      "Task needs logged-in LinkedIn or internal SSO",
      "One operator, laptop awake during run",
    ],
    skipWhen: ["Team-wide schedule", "Laptop closed at 9:00"],
    queenswarmPath: "Browser Harness + in-process session",
    href: MANUAL_HREFS.agentsSessions,
  },
  {
    level: 3,
    id: "cloud-schedule",
    title: "Cloud schedule (cron)",
    summary: "SupervisorRoutine on Celery — runs without your laptop.",
    whenToUse: [
      "Daily/weekly digest for whole tenant",
      "Verified recipe should repeat on cron",
      "Four Lanes / Operator Loop background work",
    ],
    skipWhen: ["Instant reaction to external event", "Needs local browser login"],
    queenswarmPath: "Routines · Recipe → Routine · Four Lanes",
    href: MANUAL_HREFS.agentsSessions,
  },
  {
    level: 4,
    id: "webhook",
    title: "Event webhook (API)",
    summary: "Fireflies / Calendly / Stripe → Make/n8n → Queenswarm webhook → session.",
    whenToUse: [
      "Event-driven follow-ups (meeting ended, form submit)",
      "Upstream app cannot shape Anthropic-style headers natively",
    ],
    skipWhen: ["Simple cron is enough", "Deterministic pipe with zero judgment"],
    queenswarmPath: "Routine webhook ingress · POST text payload",
    href: MANUAL_HREFS.manualAutomationLadder,
  },
  {
    level: 5,
    id: "goal-mode",
    title: "Goal mode (multi-iteration)",
    summary: "Queen GoalOrchestrator — runs until done or budget exhausted (no step babysitting).",
    whenToUse: [
      "Multi-step project with audit loop",
      "Decompose → execute → reflect until acceptance criteria met",
    ],
    skipWhen: ["Single session report is enough", "Strict simulate-only lane with critic"],
    queenswarmPath: "Knowledge → Goals · POST /goals",
    href: MANUAL_HREFS.knowledgeGoals,
  },
];

export const AUTOMATION_HYBRID_RULE =
  "Judgment/research → Queenswarm. Deterministic app sync (Stripe→accounting) → n8n/Make. Never run dumb pipes through LLM.";
