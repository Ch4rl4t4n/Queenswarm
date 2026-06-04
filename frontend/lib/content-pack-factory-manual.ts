/** Content Pack Factory operator manual — steps, hints, and recommendations (in-app Guide tab). */

import { MANUAL_HREFS } from "@/lib/manual-routes";

export interface ContentPackFactoryManualStep {
  id: string;
  phase: number;
  title: string;
  summary: string;
  hint: string;
  actions: string[];
  link?: { href: string; label: string };
  optional?: boolean;
}

export interface ContentPackFactoryPrerequisite {
  id: string;
  label: string;
  detail: string;
  href?: string;
}

export interface ContentPackFactoryRecommendation {
  id: string;
  title: string;
  body: string;
}

export const CONTENT_PACK_FACTORY_PREREQUISITES: ContentPackFactoryPrerequisite[] = [
  {
    id: "llm-keys",
    label: "LLM keys configured",
    detail:
      "Settings → AI · LLM keys — OpenAI gpt-4o-mini recommended. Run factory_llm_readiness.py --smoke on the server before Build.",
    href: MANUAL_HREFS.settingsLlmKeys,
  },
  {
    id: "auto-approve",
    label: "Auto-approve ON (solo)",
    detail: "Agents → Sessions — factory sub-steps should not stall on every micro-approval.",
    href: MANUAL_HREFS.agentsSessions,
  },
  {
    id: "pack-factory-flag",
    label: "Content Pack Factory enabled",
    detail: "CONTENT_PACK_FACTORY_ENABLED=true (default). Toggle in Automation policy if disabled.",
  },
  {
    id: "celery",
    label: "Celery worker healthy",
    detail: "Build sessions resume on celery-worker after approve. Check /health/ready after deploy.",
  },
  {
    id: "research-keys",
    label: "Research keys (optional)",
    detail: "Tavily/Serper in Settings → API keys improve demand scores — builds work without them.",
    href: "/settings/api-keys#research-keys",
  },
];

export const CONTENT_PACK_FACTORY_STEPS: ContentPackFactoryManualStep[] = [
  {
    id: "settings-seeds",
    phase: 1,
    title: "1. Niche seeds & policy",
    summary: "Define 3–8 social/content niches — Instagram calendars, LinkedIn B2B, TikTok hooks, newsletter launches.",
    hint: "Click Apply vertical starter for 8 Tier-A presets. Save policy after every change.",
    actions: [
      "Pack factory → Automation policy",
      "Apply vertical starter or add custom seeds",
      "Optional: enable auto-build after first successful pack",
      "Save policy",
    ],
  },
  {
    id: "research-run",
    phase: 2,
    title: "2. Run research",
    summary: "HiveMind heuristics rank opportunities by demand, competition, and buildability.",
    hint: "Composite ≥72% = auto-build eligible when auto-build ON. Dismiss niches outside your brand.",
    actions: [
      "Run research now",
      "Read rationale on each card",
      "Note suggested price anchor (€14–€44 typical)",
    ],
  },
  {
    id: "build-start",
    phase: 3,
    title: "3. Build content pack",
    summary: "Starts a supervisor session — researcher → coder → critic must output publish_pack JSON.",
    hint: "If LLM smoke fails, builds will fail quality gate. Fix OpenAI key first — do not parallel-build.",
    actions: [
      "Build on top pending opportunity",
      "Open session in Agents → Sessions",
      "If needs_input — reply or run factory_unblock_builds.py on server",
    ],
    link: { href: "/agents#sessions", label: "Agents → Sessions" },
  },
  {
    id: "approve-forge",
    phase: 4,
    title: "4. Approve verified_content_pack_forge",
    summary: "After verify, critic proposes forge — approve saves pack to Library.",
    hint: "Proposal type must be verified_content_pack_forge (not skill_forge). Reject wrong-type forges.",
    actions: [
      "Agents → Suggestions",
      "Approve verified_content_pack_forge",
      "Library tab fills with verified pack",
    ],
    link: { href: "/agents", label: "Agents → Suggestions" },
  },
  {
    id: "library-export",
    phase: 5,
    title: "5. Export & sell",
    summary: "Download PACK.md + LISTING.md + publish_pack.json — Gumroad-ready bundle.",
    hint: "Gumroad draft button appears when SKILL_FACTORY_GUMROAD_LISTING_ENABLED + token configured.",
    actions: [
      "Library → Export",
      "Gumroad draft (optional API)",
      "Or manual upload from LISTING.md body",
    ],
  },
];

export const CONTENT_PACK_FACTORY_RECOMMENDATIONS: ContentPackFactoryRecommendation[] = [
  {
    id: "llm-first",
    title: "Fix LLM before bulk builds",
    body: "Run factory_llm_readiness.py --smoke. Invalid Grok + empty Anthropic credits = every build fails at quality gate.",
  },
  {
    id: "one-build",
    title: "One pack build at a time",
    body: "Researcher→coder→critic chains degrade when parallel factory sessions compete for LLM budget.",
  },
  {
    id: "simulate-first",
    title: "Never skip verify",
    body: "Only approve forge when critic APPROVE + publish_pack JSON present. Raw LLM text is not a product.",
  },
  {
    id: "skills-plus-packs",
    title: "Pair with Skill Factory",
    body: "Sell agent skills (Skill Factory) + content packs (this lane) to the same niche — e.g. newsletter growth skill + 30-day content calendar.",
  },
];

export const CONTENT_PACK_FACTORY_MANUAL_DOC = "docs/CONTENT_PACK_FACTORY_OPERATOR_MANUAL.md";
export const FACTORY_FIRST_REVENUE_MANUAL_DOC = "docs/FACTORY_FIRST_REVENUE_OPERATOR_MANUAL.md";
