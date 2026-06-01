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
        text: "Knowledge — write PROJECT brief (goal, deliverables, language, simulate-first).",
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
      { text: "Knowledge — briefs + HiveMind.", href: MANUAL_HREFS.knowledge },
      { text: "Four Lanes — automated digests only (optional).", href: MANUAL_HREFS.agenticOsLanes, linkLabel: "Four Lanes" },
      { text: "Ballroom — incidents (rare).", href: MANUAL_HREFS.ballroom },
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
        label: "Knowledge → Curated memory",
        description: "Project brief before the first session — Queen injects it into every run.",
        options: ["instructions / mission", "PROJECT blocks", "Export .md backup"],
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
        description: "Search existing context and historical outputs.",
        options: ["Filter by topic", "Reuse prior solutions"],
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

