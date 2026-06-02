import { MANUAL_HREFS } from "@/lib/manual-routes";

export interface ManualChecklistItem {
  text: string;
  href?: string;
  linkLabel?: string;
}

export interface ManualSection {
  id: string;
  title: string;
  paragraphs: string[];
  checklist?: ManualChecklistItem[];
}

export interface FunctionInfoItem {
  id: string;
  label: string;
  description: string;
  options: string[];
  href?: string;
}

export interface FunctionInfoGroup {
  id: string;
  title: string;
  items: FunctionInfoItem[];
}

export const APP_MANUAL_SECTIONS: ManualSection[] = [
  {
    id: "canonical-workflow",
    title: "0. Canonical workflow (the only primary path)",
    paragraphs: [
      `Start Queenswarm via [Agents → Sessions](${MANUAL_HREFS.agentsSessions}) with a structured goal. [Swarms](${MANUAL_HREFS.swarms}), Four Lanes, and [Agentic OS](${MANUAL_HREFS.agenticOs}) are optional — not how you launch a major project.`,
      `Each major project = its own session (3–5 in parallel). Keep project briefs in [Knowledge → Curated memory](${MANUAL_HREFS.knowledgeCurated}).`,
      "Full doc: docs/OPERATOR_CANONICAL_WORKFLOW.md",
    ],
    checklist: [
      {
        text: "Knowledge — write PROJECT brief (goal, deliverables, language, simulate-first). Optional: verify Wiki Layer tier after brief.",
        href: MANUAL_HREFS.knowledgeCurated,
        linkLabel: "Curated memory",
      },
      {
        text: "Agents — Session goal (Goal → Context → Constraints → Done).",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Agents",
      },
      {
        text: "Runtime durable · Roles researcher + designer + critic · Create session.",
        href: MANUAL_HREFS.agents,
      },
      {
        text: "When done — Info → report. Next phase = new session or Tasks.",
        href: MANUAL_HREFS.tasks,
        linkLabel: "Tasks",
      },
    ],
  },
  {
    id: "setup-once",
    title: "1. One-time setup",
    paragraphs: [
      `Before first session: [LLM keys](${MANUAL_HREFS.settingsLlmKeys}), optional Tavily ([Settings → API keys](${MANUAL_HREFS.settingsApiKeys}#research-keys)), [2FA](${MANUAL_HREFS.settingsSecurity}), [Auto-approve](${MANUAL_HREFS.agentsSessions}) ON.`,
      `Set [2FA re-verification to 4 hours](${MANUAL_HREFS.settingsSecurity}) — password-only login within the window.`,
    ],
    checklist: [
      {
        text: "Log in via /login and confirm you land on {HOME_ROUTE} ({HOME_LABEL}).",
      },
      {
        text: "Settings → AI · LLM keys — Grok/Claude/GPT, Test each key.",
        href: MANUAL_HREFS.settingsLlmKeys,
        linkLabel: "LLM keys",
      },
      {
        text: "Settings → Security — 2FA + Session policy (4h re-verification).",
        href: MANUAL_HREFS.settingsSecurity,
        linkLabel: "Security",
      },
      {
        text: "Agents — Auto-approve on for solo mode.",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Agents",
      },
      {
        text: "Execution Studio → Notifications — email/Telegram digest.",
        href: MANUAL_HREFS.integrationsStudioNotifications,
        linkLabel: "Notifications",
      },
    ],
  },
  {
    id: "start-project",
    title: "2. Start a project (step by step)",
    paragraphs: [
      `Open [Agents → Sessions](${MANUAL_HREFS.agentsSessions}). Paste a structured goal — not a one-liner. Use durable runtime for redesign, campaigns, analysis.`,
      "Goal template: PROJECT + numbered deliverables + Critic APPROVE + Simulate only.",
    ],
    checklist: [
      {
        text: "1) Brief in Knowledge  2) Goal in Agents  3) durable + roles  4) Create  5) Info report  6) Task or phase 2.",
        href: MANUAL_HREFS.agentsSessions,
      },
      {
        text: "Parallel work: one session per project — never mix multiple projects in one prompt.",
        href: MANUAL_HREFS.knowledgeCurated,
        linkLabel: "Brief first",
      },
    ],
  },
  {
    id: "daily-loop",
    title: "3. Daily loop (5 min)",
    paragraphs: [
      `Email/Telegram digest → [Agents completed sessions](${MANUAL_HREFS.agentsSessions}) → Info report → [Tasks priority](${MANUAL_HREFS.tasks}) → new session for next phase.`,
      `[Agentic OS](${MANUAL_HREFS.agenticOs}), Swarm Fleet, and Swarm Builder are not your first step of the day.`,
    ],
    checklist: [
      {
        text: "Read the work digest email (not the technical audit log).",
        href: MANUAL_HREFS.integrationsStudioNotifications,
        linkLabel: "Digest settings",
      },
      {
        text: "Approved reports → Tasks or follow-up session.",
        href: MANUAL_HREFS.tasks,
        linkLabel: "Tasks",
      },
      {
        text: "Stuck running > 10 → delete in Agents (filter + clear).",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Agents",
      },
    ],
  },
  {
    id: "sections-map",
    title: "4. Section map — what to use",
    paragraphs: [
      `Daily: [Agents](${MANUAL_HREFS.agents}), [Tasks](${MANUAL_HREFS.tasks}), [Knowledge](${MANUAL_HREFS.knowledge}), [Settings](${MANUAL_HREFS.settingsSecurity}) (rare). Weekly/optional: [Agentic OS](${MANUAL_HREFS.agenticOs}), [Integrations](${MANUAL_HREFS.integrations}). Ignore in solo: legacy VC swarms.`,
    ],
    checklist: [
      { text: "Agents — launch and reports (PRIMARY).", href: MANUAL_HREFS.agentsSessions },
      { text: "Tasks — deliverables and priorities.", href: MANUAL_HREFS.tasks },
      {
        text: "Knowledge — briefs + HiveMind + Wiki Layer hot tier.",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Wiki Layer",
      },
      { text: "Four Lanes — automated digests only (optional).", href: MANUAL_HREFS.agenticOsLanes, linkLabel: "Four Lanes" },
      { text: "Ballroom — incidents (rare).", href: MANUAL_HREFS.ballroom },
    ],
  },
  {
    id: "wiki-layer",
    title: "Wiki Layer — hot/cold memory (Karpathy tiers)",
    paragraphs: [
      `Open [Knowledge → Wiki Layer](${MANUAL_HREFS.knowledgeWiki}). Three zones split what the Queen reads every prompt vs what stays in cold storage: **instructions** (curated harness), **wiki** (Gardener-compiled pages), **raw** (HiveMind chunks / forager dumps).`,
      `Default retrieval tier is **wiki_only** — fastest and cheapest: curated prefix + four Gardener wiki pages. Switch to **deep_raw** when you need full HiveMind vector/graph recall across projects (higher token cost).`,
      `The **Wiki Gardener** bee runs automatically every **5 minutes** (Celery beat). It consolidates verified outputs, recipes, and forager intel into wiki pages: operator-context, project-briefs, forager-insights, verified-recipes. Click **Run Wiki Gardener** for an immediate sweep.`,
      `**Obsidian export** downloads a Markdown vault zip for offline review. **Token telemetry** shows char counts from the last Queen bootstrap — verify wiki_only saves tokens vs deep_raw.`,
      `Env flags (operator): WIKI_LAYER_ENABLED, WIKI_LAYER_GARDENER_SWEEP_ENABLED, WIKI_LAYER_GARDENER_INTERVAL_SEC (default 300).`,
    ],
    checklist: [
      {
        text: "Write project brief in Curated memory (instructions zone) before first session.",
        href: MANUAL_HREFS.knowledgeCurated,
        linkLabel: "Curated memory",
      },
      {
        text: "Keep wiki_only for daily solo work; deep_raw only for cross-project deep recall.",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Retrieval tier",
      },
      {
        text: "After major deliverables — Run Gardener or wait 5 min tick to refresh wiki pages.",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Gardener",
      },
      {
        text: "Selective recall preview (HiveMind tab) shows active retrieval_tier in contract block.",
        href: MANUAL_HREFS.knowledge,
        linkLabel: "HiveMind",
      },
      {
        text: "Export Obsidian vault before large curated memory edits (backup).",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Obsidian export",
      },
    ],
  },
  {
    id: "ingest-router",
    title: "Ingest Router — YouTube, web URL, paste",
    paragraphs: [
      `Open [Knowledge → HiveMind → Ingest URL](${MANUAL_HREFS.knowledgeIngest}). **IngestRouterBee** picks the right bee: YouTube links → **YouTubeTranscriptBee** (captions, no Data API quota), other https URLs → **Research Bee** HTML extract, paste → structured brief.`,
      `Output is always a **structured brief** (summary, key points, tags) — never a raw transcript dump into the Queen prompt. Enable **Persist** to write HiveMind raw zone; enable **Run Wiki Gardener** to immediately refresh \`forager-insights\` wiki page.`,
      `YouTube videos need captions or auto-transcript. Tags \`forager:youtube\` + \`youtube_transcript\` help Gardener consolidate intel alongside channel foragers.`,
      `Env: \`YOUTUBE_TRANSCRIPT_BEE_ENABLED=true\` (default), \`RESEARCH_BEE_MAX_CHARS\`.`,
    ],
    checklist: [
      {
        text: "Paste YouTube URL → Ingest & generate brief → persist + Gardener.",
        href: MANUAL_HREFS.knowledgeIngest,
        linkLabel: "Ingest URL",
      },
      {
        text: "Verify brief landed in Wiki Layer raw zone, then forager-insights after Gardener.",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Wiki Layer",
      },
      {
        text: "Channel monitoring still uses Foragers + YOUTUBE_API_KEY for delta scrape.",
        href: MANUAL_HREFS.foragers,
        linkLabel: "Foragers",
      },
    ],
  },
  {
    id: "skill-hot-tier",
    title: "Skill Hot Tier — Karpathy skills × Wiki Layer",
    paragraphs: [
      `Inspired by [Karpathy's Skills](https://www.youtube.com/watch?v=pCqpuHA8kHM) — load **only relevant** skill modules per task, not the entire library. In Queenswarm: **verified recipes** = skills; **SkillHotTierBee** token-matches session goal → injects top 3 recipe summaries into Queen prompt alongside Wiki Layer.`,
      `Static compile: Wiki Gardener \`verified-recipes\` page (hot tier, all tenants). Dynamic compile: **Skill Hot Tier** per session goal (marketing digest goal → marketing recipes only).`,
      `This avoids prompt bloat from dumping every SKILL.md / recipe into context — same philosophy as \`wiki_only\` skipping raw RAG.`,
      `Env: \`SKILL_HOT_TIER_ENABLED=true\`, \`SKILL_HOT_TIER_MAX_RECIPES=3\`, \`SKILL_HOT_TIER_MIN_SCORE=0.12\`.`,
      `Not imported from Claude Code plugins — native hive bees with pollen + simulate guardrails.`,
    ],
    checklist: [
      {
        text: "Verify recipes in Recipe Library before expecting hot-tier matches.",
        href: MANUAL_HREFS.knowledgeRecipes,
        linkLabel: "Recipes",
      },
      {
        text: "Write structured session goals with domain keywords (marketing, digest, e-shop…).",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Agents",
      },
      {
        text: "Pair with Wiki Layer wiki_only — hot skills + hot wiki, cold raw.",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Wiki Layer",
      },
    ],
  },
  {
    id: "lead-gen-lane",
    title: "Lead Gen Lane — verified outreach pipeline",
    paragraphs: [
      `Simulate-first alternative to lead-gen agencies ([reference video](https://www.youtube.com/watch?v=qw0xdTtzK1w)). Recipe: **Verified — Lead Gen Lane** (5 steps). Bees: **Lead Scout** + **Outreach Draft** — never live send.`,
      `**One-click launch:** [Agents → preset Lead Gen Lane](${MANUAL_HREFS.agentsLeadGenLane}) · [Tasks → Mission Kanban bundle](${MANUAL_HREFS.tasks}) · [Agentic OS → Quick automation](${MANUAL_HREFS.agenticOs})`,
      `Before run: write **ICP** in [Curated memory](${MANUAL_HREFS.knowledgeCurated}) — industry, size, region, signal. Optional: ingest competitor video/article via [Ingest URL](${MANUAL_HREFS.knowledgeIngest}) → Gardener updates forager-insights.`,
      `Flow: ICP summary → Lead Scout (≤10 leads, HiveMind tags \`lead\`, \`account\`) → optional public intel → Outreach Draft (≤5, Gmail simulate_only) → Critic APPROVE → report.`,
      `Skill Hot Tier auto-matches this recipe when session goal contains lead/outreach/ICP keywords.`,
    ],
    checklist: [
      {
        text: "1) ICP in Curated memory  2) Agents → Lead Gen Lane preset  3) Fill ICP blanks in goal  4) durable + critic  5) Review simulate drafts",
        href: MANUAL_HREFS.agentsLeadGenLane,
        linkLabel: "Launch preset",
      },
      {
        text: "Never approve live Gmail send without explicit operator OK.",
        href: MANUAL_HREFS.integrationsStudio,
        linkLabel: "Execution Studio",
      },
      {
        text: "After run — check Wiki Layer forager-insights + Recipe Library match.",
        href: MANUAL_HREFS.knowledgeWiki,
        linkLabel: "Wiki Layer",
      },
    ],
  },
  {
    id: "pattern-router",
    title: "Pattern Router — agentic design patterns per session",
    paragraphs: [
      `On every **Create session**, Queenswarm runs the **Pattern Router** — a heuristic stack of Kashef-style agentic patterns (planning, RAG, guardrails, reflection, …) chosen from your goal text and sub-agent roles.`,
      `You see the selection in three places: **live preview** under the goal field (before Create), **badges on each session row**, and the full breakdown in **Info → Session report → Pattern Router**.`,
      `Patterns map to **skill hints** (e.g. reflection → \`self-review-loop\`) merged with your requested skill pack. Final per-role skills appear after spawn in the report.`,
      `Optional **LLM refinement** (\`SUPERVISOR_PATTERN_ROUTER_LLM_ENABLED\`) re-ranks patterns; badge shows \`LLM-refined\` vs \`heuristic-v1\`. **Forced reflection** keeps Critic → Revise → Validate before verified output.`,
      `Tenant-wide catalog and recent usage: [Settings → Harness → Pattern Explorer](${MANUAL_HREFS.settingsHarness}). Full pattern list: \`docs/QUEENSWARM_DESIGN_PATTERNS.md\`.`,
    ],
    checklist: [
      {
        text: "Write a specific goal — keywords steer parallelization, tool use, HITL, exploration.",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Agents sessions",
      },
      {
        text: "Check preview badges before Create — adjust goal or roles if the stack looks wrong.",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Goal preview",
      },
      {
        text: "After run — Info report shows resolved skills by role + pattern rationale.",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Session report",
      },
      {
        text: "Harness Pattern Explorer — catalog + 24h usage across sessions.",
        href: MANUAL_HREFS.settingsHarness,
        linkLabel: "Pattern Explorer",
      },
    ],
  },
  {
    id: "automation-ladder",
    title: "Automation Ladder — stop babysitting Claude (L1–L5)",
    paragraphs: [
      `Framework from [Brad's automation video](https://www.youtube.com/watch?v=1RdkW1zqv-U): five levels from on-demand skills to hosted agents. Queenswarm maps each level to native bees — **no single answer fits every workflow**.`,
      `**L1 Skills & presets** — Pattern Router preview + session presets. You still click Create. Best for repeatable missions with changing inputs.`,
      `**L2 Desktop / browser** — [Browser Harness](${MANUAL_HREFS.agentsSessions}) with logged-in Chrome. Your laptop must be awake.`,
      `**L3 Cloud schedule** — [Supervisor Routines](${MANUAL_HREFS.agentsSessions}) (cron/Celery) or **Recipe → Routine**: \`POST /api/v1/recipes/{id}/routine\`. Runs when laptop is closed.`,
      `**L4 Event webhook** — Enable webhook on a routine → copy URL + token → Make/n8n middleware shapes payload as \`{"text":"..."}\` + header \`X-Queenswarm-Webhook-Token\`. Spawns durable session with EVENT CONTEXT appended to goal.`,
      `**L5 Goal mode** — [Knowledge → Goals](${MANUAL_HREFS.knowledgeGoals}): Queen GoalOrchestrator iterates until done/budget. Multi-step projects without pressing Enter each turn.`,
      `**Hybrid rule:** judgment/research → Queenswarm. Deterministic pipes (Stripe→accounting) → n8n/Make — never burn LLM tokens on dumb sync.`,
      `Env: \`ROUTINES_ENABLED=true\`, \`SUPERVISOR_ROUTINE_WEBHOOK_ENABLED=true\`. Audit: \`./scripts/operator-automation-ladder-audit.sh\`.`,
    ],
    checklist: [
      { text: "L1 — preset + Pattern preview → Create session", href: MANUAL_HREFS.agentsSessions, linkLabel: "Agents" },
      { text: "L3 — verified recipe → cron routine", href: MANUAL_HREFS.knowledgeRecipes, linkLabel: "Recipes" },
      { text: "L4 — routine webhook + Make middleware", href: MANUAL_HREFS.agentsSessions, linkLabel: "Webhook controls" },
      { text: "L5 — multi-iteration Queen goal", href: MANUAL_HREFS.knowledgeGoals, linkLabel: "Goals" },
      { text: "Run automation ladder audit after changes", href: MANUAL_HREFS.manualAutomationLadder, linkLabel: "Audit script" },
    ],
  },
  {
    id: "agent-workflows",
    title: "Agent workflow catalog (when to use which lane)",
    paragraphs: [
      `Verified recipes and presets agents should prefer — each is simulate-first, one sharp job per bee.`,
      `**Lead Gen Lane** — B2B outreach drafts from HiveMind ([manual](${MANUAL_HREFS.manualLeadGenLane})).`,
      `**Marketing campaign** — audience, channels, 2-week calendar, publish pack simulate ([Agents preset](${MANUAL_HREFS.agentsSessions})).`,
      `**Competitor research** — top 5 + gap analysis ([preset](${MANUAL_HREFS.agentsSessions}) + skill \`competitor-scrape-analyze\`).`,
      `**Ingest URL** — YouTube transcript or article → brief → Gardener ([Knowledge](${MANUAL_HREFS.knowledgeIngest})).`,
      `**Four Lanes digest** — cron marketing/e-shop intel (optional background, not primary path).`,
      `**Web redesign discovery** — UX audit + IA ([Agents preset](${MANUAL_HREFS.agentsSessions})).`,
      `Agents pick workflows via **Skill Hot Tier** (goal match) + **Recipe Library** cosine ≥0.85 — never load all skills at once.`,
    ],
    checklist: [
      { text: "Lead Gen — sales/outreach/ICP goals", href: MANUAL_HREFS.agentsLeadGenLane, linkLabel: "Lead Gen Lane" },
      { text: "Marketing — campaign, publish, social", href: MANUAL_HREFS.agentsSessions, linkLabel: "Marketing preset" },
      { text: "Research — competitor, ingest, foragers", href: MANUAL_HREFS.knowledgeIngest, linkLabel: "Ingest URL" },
      { text: "Wiki + skills — hot tier only", href: MANUAL_HREFS.knowledgeWiki, linkLabel: "Wiki Layer" },
    ],
  },
  {
    id: "settings-reference",
    title: "5. Settings reference",
    paragraphs: [
      `[Security](${MANUAL_HREFS.settingsSecurity}) — 2FA, session TTL, 2FA re-verification window. [LLM keys](${MANUAL_HREFS.settingsLlmKeys}) — required for sessions. [AI harness](${MANUAL_HREFS.settingsHarness}) — curated memory briefs. [Execution Studio notifications](${MANUAL_HREFS.integrationsStudioNotifications}) — email/Telegram.`,
      `[Agents panel](${MANUAL_HREFS.agentsSessions}) — Auto-approve, runtime (inprocess/durable), roles, routines.`,
    ],
    checklist: [
      {
        text: "Auto-approve ON = routine without manual clicks; critical actions stay manual.",
        href: MANUAL_HREFS.agentsSessions,
        linkLabel: "Agents",
      },
      {
        text: "durable runtime = long projects; inprocess = quick short tasks.",
        href: MANUAL_HREFS.agents,
      },
      {
        text: "Session policy 4h custom = Authenticator only once every 4 hours.",
        href: MANUAL_HREFS.settingsSecurity,
        linkLabel: "Security",
      },
    ],
  },
  {
    id: "background-automation",
    title: "6. Optional automation (not the main path)",
    paragraphs: [
      `[Four Lanes](${MANUAL_HREFS.agenticOsLanes}) — 4 cron digests, bootstrap once, then approve. [Foragers](${MANUAL_HREFS.foragers}) — intel into HiveMind. [Tasks → Routines](${MANUAL_HREFS.tasks}) — repeat the same goal template.`,
      "Sub-swarms in DB are bee infrastructure — you do not need a new swarm per project.",
    ],
    checklist: [
      {
        text: "Four Lanes doc: docs/SOLO_OPERATOR_FOUR_LANE.md",
        href: MANUAL_HREFS.agenticOsLanes,
        linkLabel: "Four Lanes",
      },
      {
        text: "Digest Inbox → Task for marketing/e-shop digests only.",
        href: MANUAL_HREFS.agenticOsLanes,
        linkLabel: "Digest inbox",
      },
      {
        text: "Tech proposals → Innovation Lab, not Four Lanes.",
        href: MANUAL_HREFS.integrationsStudioInnovation,
        linkLabel: "Innovation Lab",
      },
    ],
  },
  {
    id: "troubleshooting",
    title: "7. Troubleshooting",
    paragraphs: [
      `Session failed → [LLM keys](${MANUAL_HREFS.settingsLlmKeys}). Empty report → still running. needs_input → [approve or auto-approve](${MANUAL_HREFS.agentsSessions}). Too many UI options → follow [sections 0–3](${MANUAL_HREFS.manualCanonical}) of this manual.`,
    ],
    checklist: [
      {
        text: "Login redirect → session expired, sign in again.",
        href: MANUAL_HREFS.login,
        linkLabel: "Login",
      },
      { text: "401 auth · 403 permission · 404 route drift.", href: MANUAL_HREFS.settingsSecurity },
    ],
  },
  {
    id: "voice-providers",
    title: "8. Voice providers (optional)",
    paragraphs: [
      `In [Settings → AI + Voice keys](${MANUAL_HREFS.settingsLlmKeys}) store Grok/Deepgram/OpenAI (STT) and Grok/ElevenLabs/OpenAI (TTS) keys.`,
      `Choose STT/TTS priority in the same panel. On failures, server-side fallback applies automatically.`,
      `[Ballroom](${MANUAL_HREFS.ballroom}) chat includes quick templates and @AgentName mentions.`,
    ],
    checklist: [
      {
        text: "Save API keys, test each provider, then select STT/TTS preference.",
        href: MANUAL_HREFS.settingsLlmKeys,
        linkLabel: "Voice keys",
      },
      {
        text: "Verify in Ballroom that voice input is processed server-side.",
        href: MANUAL_HREFS.ballroom,
        linkLabel: "Ballroom",
      },
      {
        text: "If slow, switch Response mode to Fast and tune VAD / silence in Advanced voice.",
        href: MANUAL_HREFS.settingsLlmKeys,
      },
    ],
  },
];

export const APP_FUNCTION_GUIDE: FunctionInfoGroup[] = [
  {
    id: "canonical",
    title: "0. Canonical workflow (always start here)",
    items: [
      {
        id: "canonical-session",
        label: "Agents → New session",
        description:
          "Primary path: write a PROJECT goal, durable runtime, researcher+critic, Create → Info report → Tasks or phase 2.",
        options: [
          "Goal → Context → Constraints → Done",
          "One project = one session",
          "Manual #canonical-workflow",
        ],
      },
      {
        id: "canonical-knowledge",
        label: "Knowledge → Curated memory + Wiki Layer",
        description:
          "Project brief before the first session — Queen injects curated memory (instructions zone) plus Gardener wiki pages (hot tier) into every run.",
        options: [
          "Curated memory — instructions / mission / PROJECT blocks",
          "Wiki Layer — wiki_only (default) or deep_raw tier",
          "Gardener — auto every 5 min, manual Run for immediate refresh",
          "Export .md backup from curated memory or Obsidian zip from Wiki tab",
        ],
        href: MANUAL_HREFS.knowledgeWiki,
      },
      {
        id: "canonical-tasks",
        label: "Tasks",
        description: "Deliverables after an approved report — not how you start work.",
        options: ["Priority", "Link from session promote", "Weekly review"],
      },
    ],
  },
  {
    id: "dashboard",
    title: "Dashboard",
    items: [
      {
        id: "cockpit-home",
        label: "Agentic OS",
        description: "Solo Operator Control Plane — one entry for swarms, Factory, Innovation Lab, and verify-first actions.",
        options: ["Start day / Trio cycle", "Bee Hotline routing"],
      },
      {
        id: "dashboard-overview",
        label: "Live dashboard",
        description: "Advanced ColonyConsole — full Queen dashboard with agents, tasks, and live swarm network.",
        options: ["Open swarms/costs/monitoring details", "Quick orientation before action"],
      },
      {
        id: "dashboard-monitoring",
        label: "Monitoring",
        description: "Host pressure, queues, and telemetry diagnostics.",
        options: ["Track performance drift", "Review incident signals"],
      },
    ],
  },
  {
    id: "agents",
    title: "Agents + Supervisor",
    items: [
      {
        id: "agents-session",
        label: "Supervisor sessions",
        description:
          "Primary OS control. Launch projects here — not via Swarm Builder or Agentic OS Lanes.",
        options: [
          "Create session — structured goal",
          "Auto-approve ON (solo)",
          "Info → PDF report",
          "durable runtime for large projects",
        ],
      },
      {
        id: "agents-spawn",
        label: "Spawn agent",
        description: "Create a new agent within swarm orchestration.",
        options: ["Define role", "Assign swarm lane", "Initial settings"],
      },
      {
        id: "agents-foragers",
        label: "Foragers",
        description: "Dynamic ingest workers wired to routines, HiveMind, and spawn flow.",
        options: ["Forager CRUD", "Source/filter config", "Manual ingest and agent spawn"],
      },
      {
        id: "lead-gen-lane",
        label: "Lead Gen Lane preset",
        description:
          "One-click simulate-first outreach: ICP → Lead Scout ≤10 → Outreach Draft ≤5. Verified recipe LEAD_GEN_LANE.",
        options: [
          "Agents → preset chip Lead Gen Lane",
          "Fill ICP in goal before Create",
          "Gmail simulate_only — no live send",
        ],
        href: MANUAL_HREFS.agentsLeadGenLane,
      },
      {
        id: "pattern-router",
        label: "Pattern Router visibility",
        description:
          "Live preview under goal + session row badges + Info report — shows which agentic patterns and skills were selected.",
        options: [
          "Preview before Create session",
          "Primary/secondary pattern badges per row",
          "Resolved skills by sub-agent role in report",
        ],
        href: MANUAL_HREFS.manualPatternRouter,
      },
      {
        id: "automation-ladder",
        label: "Automation Ladder (L1–L5)",
        description:
          "When to use presets, browser harness, cron routines, webhooks, or Goal mode — hybrid with n8n/Make for dumb pipes.",
        options: [
          "L3 Recipe → Routine one-click API",
          "L4 Webhook ingress on routines",
          "L5 Goals in Knowledge tab",
        ],
        href: MANUAL_HREFS.manualAutomationLadder,
      },
    ],
  },
  {
    id: "tasks",
    title: "Tasks + Routines",
    items: [
      {
        id: "tasks-new",
        label: "New task",
        description: "Create a new task for the execution pipeline.",
        options: ["Priority", "Goal description", "Link to workflow/session"],
      },
      {
        id: "tasks-mission-kanban",
        label: "Mission Kanban bundles",
        description: "One-click task packs including Lead Gen Lane, competitor research, content week.",
        options: [
          "Lead Gen Lane — auto-dispatch scout + outreach simulate",
          "Competitor research sprint",
          "Campaign brief — triage before dispatch",
        ],
        href: MANUAL_HREFS.tasks,
      },
      {
        id: "tasks-routines",
        label: "Routines",
        description: "Scheduled automated task flows.",
        options: ["Interval/schedule", "Enable/disable", "Last run review"],
      },
    ],
  },
  {
    id: "knowledge",
    title: "Knowledge",
    items: [
      {
        id: "knowledge-hivemind",
        label: "HiveMind retrieval",
        description: "Search existing context and historical outputs. Raw zone feeds deep_raw tier; skipped when wiki_only.",
        options: ["Filter by topic", "Reuse prior solutions", "Selective recall shows retrieval_tier"],
        href: MANUAL_HREFS.knowledge,
      },
      {
        id: "knowledge-wiki",
        label: "Wiki Layer",
        description:
          "Karpathy hot/cold tiers — compiled wiki pages in every Queen prompt; raw HiveMind optional via deep_raw.",
        options: [
          "3 zones — raw / wiki / instructions",
          "wiki_only vs deep_raw switch",
          "Gardener bee — 5 min Celery sweep",
          "Obsidian vault export",
          "Token telemetry per zone",
        ],
        href: MANUAL_HREFS.knowledgeWiki,
      },
      {
        id: "knowledge-wiki-gardener",
        label: "Wiki Gardener",
        description:
          "Background bee that sweeps verified outputs into four wiki pages. Earns pollen on verified updates.",
        options: [
          "Auto tick every 5 minutes",
          "Run Wiki Gardener — immediate sweep",
          "Pages: operator-context, project-briefs, forager-insights, verified-recipes",
        ],
        href: MANUAL_HREFS.knowledgeWiki,
      },
      {
        id: "knowledge-wiki-obsidian",
        label: "Obsidian export",
        description: "Download wiki pages as Markdown zip — frontmatter with slug, version, updated_at.",
        options: ["Read-only export", "Obsidian / Logseq compatible", "Backup before curated edits"],
        href: MANUAL_HREFS.knowledgeWiki,
      },
      {
        id: "knowledge-ingest",
        label: "Ingest URL (Research Bee)",
        description:
          "IngestRouterBee — YouTube transcript, web URL, or paste → structured brief → optional HiveMind + Gardener.",
        options: [
          "YouTube watch/youtu.be/shorts auto-route",
          "Persist to raw zone + trigger Gardener",
          "Never raw dump to Queen prompt",
        ],
        href: MANUAL_HREFS.knowledgeIngest,
      },
      {
        id: "knowledge-youtube-ingest",
        label: "YouTube transcript bee",
        description: "On-demand video URL → captions/auto-transcript → brief. No YouTube Data API quota.",
        options: ["Requires captions on video", "Tags forager:youtube", "Gardener → forager-insights"],
        href: MANUAL_HREFS.knowledgeIngest,
      },
      {
        id: "knowledge-skill-hot-tier",
        label: "Skill Hot Tier",
        description:
          "Karpathy-style dynamic skill load — goal-matched verified recipes injected per Queen session.",
        options: [
          "Max 3 recipes per session",
          "Token overlap scoring",
          "Complements Wiki verified-recipes page",
        ],
        href: MANUAL_HREFS.manualSkillHotTier,
      },
      {
        id: "knowledge-outputs",
        label: "Outputs archive",
        description: "Archive and reuse delivered outputs.",
        options: ["Quality review", "Link to follow-up tasks"],
      },
      {
        id: "knowledge-dreaming",
        label: "Memory + Dreaming",
        description: "Auto-consolidate lessons from supervisor sessions into HiveMind.",
        options: ["Enable/disable", "Frequency", "Manual trigger + Dream Reports"],
      },
    ],
  },
  {
    id: "integrations",
    title: "Integrations",
    items: [
      {
        id: "integrations-connectors",
        label: "Dynamic Connector Hub",
        description: "Manage connectors, auth state, and connection tests.",
        options: ["Connector create/update", "Connection test", "Vault sync"],
      },
      {
        id: "integrations-marketplace",
        label: "Tools Marketplace",
        description: "Install API tools and expose them to supervisor lanes.",
        options: ["One-click install", "Browse tool catalog"],
      },
    ],
  },
  {
    id: "operator-cockpit",
    title: "Agentic OS",
    items: [
      {
        id: "cockpit-four-lanes",
        label: "Four Lanes (optional)",
        description:
          "Automated cron digests in the background. Not a replacement for Agents sessions on major projects.",
        options: [
          "Bootstrap once",
          "Digest Inbox approve → task",
          "Manual #background-automation",
        ],
      },
      {
        id: "cockpit-digest-inbox",
        label: "Digest Inbox",
        description:
          "Queue of four-lane digest sessions — review excerpt, open session, promote to Tasks (marketing/e-shop).",
        options: ["→ Task one-click", "Tech SCV → Innovation Lab"],
      },
      {
        id: "cockpit-overview",
        label: "Operator overview",
        description:
          "Daily command surface — prioritized actions, Oracle warnings, Trust Autopilot lanes, and Proof-of-Hive receipts.",
        options: ["Start day (trio cycle)", "Refresh core snapshot", "Jump to Factory / Swarms / Agents"],
      },
      {
        id: "cockpit-command",
        label: "Command lane",
        description: "Hotline, Intent Crystallizer, and Zero-UI Telegram — three ways to drive the hive without hunting panels.",
        options: ["Natural language Hotline", "Crystallizer preview/launch", "Telegram /day /status /hotline"],
      },
      {
        id: "bee-hotline",
        label: "Bee Hotline",
        description: "Plain-language request → routed Queen goal on the correct bee lane.",
        options: ["One sentence operator intent", "Server action hotline", "No manual nav required"],
      },
      {
        id: "intent-crystallizer",
        label: "Intent Crystallizer",
        description: "Free text → swarm templates, trust lane, and deep links before launching Queen.",
        options: ["Preview plan", "Launch Queen goal", "Trust lane auto/simulate/live"],
      },
      {
        id: "zero-ui-hive",
        label: "Zero-UI Hive Mode",
        description: "Telegram commands mirror Agentic OS — optional web UI after bot + webhook setup.",
        options: ["Execution Studio notifications", "Webhook URL + secret", "/help command list"],
      },
      {
        id: "icm-tools",
        label: "ICM tools",
        description: "Link drop, dialogue extract, and quick automations — capture intent without the swarm builder.",
        options: ["URL → brief → Knowledge", "Transcript → harness/knowledge/recipe", "Quick automation presets"],
      },
      {
        id: "swarm-fleet",
        label: "Swarm Fleet",
        description: "Always-on routines with pause/resume and immune watch/quarantine signals.",
        options: ["Pause/resume routine", "Autopilot schedule", "Immune system recommendations"],
      },
      {
        id: "cockpit-modules",
        label: "Futurist modules",
        description: "Lazy-loaded experimental modules — Regret, Teleport, Ambient, Parallel, Evolutionary Recipes.",
        options: ["On-demand load", "Verified outcomes for recipes", "No duplicate swarms"],
      },
      {
        id: "innovation-lab",
        label: "Innovation Lab",
        description: "Brainstorm → approve → Queen Maintainer PR-only implementation.",
        options: ["Brainstorm proposal", "Approve/reject gate", "Implement via Maintainer"],
      },
    ],
  },
  {
    id: "ballroom",
    title: "Ballroom",
    items: [
      {
        id: "ballroom-realtime",
        label: "Realtime lane",
        description: "Live coordination during incidents and critical deploy flows.",
        options: ["Fast ops lane", "Link to Supervisor sessions"],
      },
    ],
  },
  {
    id: "settings",
    title: "Settings",
    items: [
      {
        id: "settings-security",
        label: "Security",
        description: "2FA, auth guards, and account security rules.",
        options: ["TOTP setup", "Session security", "Auth preference"],
      },
      {
        id: "settings-team",
        label: "Team RBAC",
        description: "Role-based access control for tenant members.",
        options: ["Role assignment", "Permission governance", "Access revocation"],
      },
      {
        id: "settings-billing",
        label: "Billing/Usage",
        description: "Budgets, usage signals, and cost limits.",
        options: ["Spend tracking", "Budget alerts", "Usage review"],
      },
      {
        id: "settings-voice-providers",
        label: "AI + Voice keys",
        description: "Manage LLM/STT/TTS API keys and voice pipeline provider priority.",
        options: ["Grok/Deepgram/OpenAI for STT", "Grok/ElevenLabs/OpenAI for TTS", "Auto fallback on outage"],
      },
    ],
  },
];

