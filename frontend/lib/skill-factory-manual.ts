/** Skill Factory operator manual — steps, hints, and recommendations (in-app Guide tab). */

import { MANUAL_HREFS } from "@/lib/manual-routes";

export interface SkillFactoryManualStep {
  id: string;
  phase: number;
  title: string;
  summary: string;
  hint: string;
  actions: string[];
  link?: { href: string; label: string };
  optional?: boolean;
}

export interface SkillFactoryPrerequisite {
  id: string;
  label: string;
  detail: string;
  href?: string;
}

export interface SkillFactoryRecommendation {
  id: string;
  title: string;
  body: string;
}

export interface SkillFactoryGapItem {
  id: string;
  label: string;
  status: "done" | "operator" | "planned";
  detail: string;
}

export const SKILL_FACTORY_PREREQUISITES: SkillFactoryPrerequisite[] = [
  {
    id: "llm-keys",
    label: "LLM keys configured",
    detail: "Settings → AI · LLM keys — at least one provider (Grok recommended). Factory sessions call researcher + coder + critic bees.",
    href: MANUAL_HREFS.settingsLlmKeys,
  },
  {
    id: "auto-approve",
    label: "Auto-approve ON (solo)",
    detail: "Agents → Sessions — enable auto-approve so factory sub-steps do not stall on every micro-approval.",
    href: MANUAL_HREFS.agentsSessions,
  },
  {
    id: "skill-factory-flag",
    label: "Skill Factory enabled",
    detail: "Feature flag skill_factory ON (solo default). Settings tab → Factory enabled.",
  },
  {
    id: "celery",
    label: "Celery worker healthy",
    detail: "Weekly research cron and async workflow runs need celery-worker + beat. Check /health/ready on deploy.",
  },
  {
    id: "hivemind",
    label: "HiveMind populated (recommended)",
    detail: "Run Foragers or Ingest URL so research scores real demand signals — empty HiveMind still works with default niches.",
    href: MANUAL_HREFS.foragers,
  },
];

export const SKILL_FACTORY_STEPS: SkillFactoryManualStep[] = [
  {
    id: "settings-seeds",
    phase: 1,
    title: "1. Set niche seeds (Settings)",
    summary: "Define 3–8 topics where you want to build skills — e.g. newsletter automation, SEO blog pipeline, Cursor agent packs.",
    hint: "Empty seeds = 8 default niches (newsletter, SEO, crypto alerts…). Save policy after edits.",
    actions: [
      "Apps & Tools → Skill Factory → Settings",
      "Add niche seeds relevant to your business",
      "Set max builds/week (cost guard — we recommend 2–3)",
      "Save policy",
    ],
  },
  {
    id: "settings-auto",
    phase: 1,
    title: "1b. Auto-build (optional)",
    summary: "When score ≥ threshold, the system starts a factory session automatically — best after you trust the flow.",
    hint: "Start with auto-build OFF. Enable after your first successful manual skill. Threshold 0.72 is a good starting point.",
    actions: [
      "Auto-build OFF for the first month",
      "Min score 0.72–0.78",
      "Leave research cron ON (Monday morning)",
    ],
    optional: true,
  },
  {
    id: "research-run",
    phase: 2,
    title: "2. Run Research",
    summary: "HiveMind + Skill Market Intel score opportunities by demand, competition, and buildability.",
    hint: "Composite ≥72% = auto-build eligible. Rationale shows HiveMind hits and intel signals. Dismiss weak niches.",
    actions: [
      "Research tab → Run research now",
      "Read rationale on each card",
      "Compare suggested price (€9 / €19 / €29 anchor)",
      "Dismiss niches outside your expertise",
    ],
  },
  {
    id: "build-start",
    phase: 3,
    title: "3. Build skill",
    summary: "Starts a supervisor session with a factory goal — researcher → coder → critic → simulate.",
    hint: "One build = one session. Do not launch five at once — cost guard and quality drop.",
    actions: [
      "Click Build skill on the chosen opportunity",
      "Open Queue tab — status building",
      "Go to Agents → Sessions and watch the run",
    ],
    link: { href: "/agents#sessions", label: "Agents → Sessions" },
  },
  {
    id: "monitor-session",
    phase: 4,
    title: "4. Monitor factory session",
    summary: "Bees produce a SKILL.md draft per skill-authoring-template. Critic must APPROVE before operator review.",
    hint: "Info report shows resolved skills + pattern badges. On fail — new session with a sharper goal, not a raw-output retry.",
    actions: [
      "Sessions — find a goal containing “Skill Factory” or the niche",
      "Wait for status completed / needs_input",
      "If needs_input — add missing context in your reply",
    ],
    link: { href: "/agents#sessions", label: "Open Sessions" },
  },
  {
    id: "approve-forge",
    phase: 5,
    title: "5. Approve verified_skill_forge",
    summary: "After verify, critic proposes a forge — approve saves the skill to tenant registry + Recipe Library.",
    hint: "Without approve the skill never appears in Library or the skill picker. Reject if SKILL.md is not production-ready.",
    actions: [
      "Agents → Suggestions (or Execution Studio codebase lane)",
      "Find proposal_type verified_skill_forge",
      "Approve — tenant skill + recipe are created automatically",
    ],
    link: { href: "/agents", label: "Agents → Suggestions" },
  },
  {
    id: "library-export",
    phase: 6,
    title: "6. Export GitHub pack",
    summary: "Download bundle: SKILL.md + README.md + LISTING.md + meta.json — ready for repo or Gumroad.",
    hint: "LISTING.md is copy for your sales listing. GitHub push is manual (no auto-PR yet).",
    actions: [
      "Library tab → Download GitHub pack",
      "Unzip and review SKILL.md",
      "Push to public/private repo per your strategy",
    ],
  },
  {
    id: "use-runtime",
    phase: 7,
    title: "7. Use skill in the hive",
    summary: "Tenant skills merge into SkillLibrary — agents see them automatically or via explicit picker.",
    hint: "Empty picker = auto match from goal. Pin a factory slug when you want a specific skill.",
    actions: [
      "Agents → Sessions — Skills override chips under goal",
      "Mission Kanban — chips on triage/dispatch",
      "Tasks → New task — chips on operator intake",
    ],
    link: { href: MANUAL_HREFS.agentsSessions, label: "Sessions skill picker" },
  },
  {
    id: "external-sales",
    phase: 8,
    title: "8. Sell outside the app (optional)",
    summary: "The app does not checkout — export goes to GitHub (open/free) or Gumroad (€9–49). Marketing is on you.",
    hint: "Primary ROI = internal skills for a faster hive. External sales = cherry-pick top 1–2 per month.",
    actions: [
      "GitHub — README + topics (cursor-skill, agent-skill)",
      "Gumroad — LISTING.md as product description",
      "Do not use in-app marketplace (disabled by design)",
    ],
    optional: true,
  },
];

export const SKILL_FACTORY_RECOMMENDATIONS: SkillFactoryRecommendation[] = [
  {
    id: "internal-first",
    title: "Internal skills before selling",
    body: "The biggest value is immediate — a factory skill you use in Agents sessions daily. External sales only after 3+ successful runs.",
  },
  {
    id: "niche-specific",
    title: "Specific niche, not generic",
    body: "“Cursor agent skill” is crowded. Winners: “Newsletter growth loop for indie SaaS”, “SEO brief pipeline with simulate-first verify”.",
  },
  {
    id: "verify-always",
    title: "Never raw output to the operator",
    body: "Approve forge only after critic APPROVE + simulate. Raw LLM SKILL.md without verify belongs in draft, not Library.",
  },
  {
    id: "one-at-a-time",
    title: "One build at a time",
    body: "max_builds_per_week = 2–3. Researcher→coder→critic chain quality drops with parallel factory runs.",
  },
  {
    id: "feed-hivemind",
    title: "Feed HiveMind before research",
    body: "Foragers + Ingest URL raise Skill Market Intel scores. Empty HiveMind = default niche heuristics only.",
  },
  {
    id: "no-marketplace",
    title: "No in-app checkout",
    body: "UGC marketplace and premium checkout are disabled by design. Sales = GitHub/Gumroad with export bundle.",
  },
];

export const SKILL_FACTORY_GAPS: SkillFactoryGapItem[] = [
  {
    id: "core-pipeline",
    label: "Research → build → forge → library → export",
    status: "done",
    detail: "Backend + UI deployed to prod.",
  },
  {
    id: "skill-picker",
    label: "Skill picker (Sessions, Kanban, New task)",
    status: "done",
    detail: "Multi-select chips + execution_payload.skills.",
  },
  {
    id: "first-skill",
    label: "First verified tenant skill in Library",
    status: "operator",
    detail: "Run Build → approve forge — library stays empty until you complete one full cycle.",
  },
  {
    id: "live-scrapers",
    label: "Live GitHub/Gumroad scrapers",
    status: "planned",
    detail: "Research uses HiveMind + Skill Market Intel, not direct market scraping.",
  },
  {
    id: "github-auto-push",
    label: "Auto GitHub PR / push",
    status: "done",
    detail: "Library → Push GitHub PR when github_rest connector and env target are configured.",
  },
  {
    id: "gumroad-api",
    label: "Gumroad API listing",
    status: "done",
    detail: "Library → Gumroad draft + publish when gumroad_rest connector and env flags are set.",
  },
  {
    id: "llm-cost",
    label: "LLM budget for factory runs",
    status: "operator",
    detail: "Check Settings → costs and LLM keys before bulk auto-build.",
  },
  {
    id: "forager-tags",
    label: "Forager tag skill-opportunity",
    status: "operator",
    detail: "Optionally tag HiveMind ingest skill-opportunity for better research scores.",
  },
];

export const SKILL_FACTORY_MANUAL_DOC = "docs/SKILL_FACTORY_OPERATOR_MANUAL.md";
