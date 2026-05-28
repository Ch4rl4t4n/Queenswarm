import type { FunctionInfoGroup, ManualSection } from "@/lib/manual-content";
import { APP_FUNCTION_GUIDE, APP_MANUAL_SECTIONS } from "@/lib/manual-content";
import { hiveOverviewHref, hiveOverviewLabel } from "@/lib/hive-home-route";
import type { UiLanguage } from "@/lib/ui-language";

const MANUAL_SUBTITLE: Record<UiLanguage, string> = {
  en: "Complete guide for operating Queenswarm — every section in English with deep links from Info hints.",
  sk: "Complete guide for operating Queenswarm — every section in English with deep links from Info hints.",
};

const FUNCTION_GUIDE_INTRO: Record<UiLanguage, string> = {
  en: "Each function below has an Info icon with functionality notes and configuration options.",
  sk: "Každá funkcia nižšie má `Info` ikonu s popisom funkcionality a možností nastavenia.",
};

const FUNCTION_GUIDE_HEADING: Record<UiLanguage, string> = {
  en: "App functions and info descriptions",
  sk: "Funkcie aplikácie a info popisy",
};

/** Replace CP-aware home tokens in manual copy. */
export function interpolateManualHomeTokens(text: string): string {
  return text
    .replaceAll("{HOME_ROUTE}", hiveOverviewHref())
    .replaceAll("{HOME_LABEL}", hiveOverviewLabel());
}

function localizeManualSection(section: ManualSection, lang: UiLanguage): ManualSection {
  return {
    ...section,
    paragraphs: pickTaggedLines(section.paragraphs, lang).map(interpolateManualHomeTokens),
    checklist: section.checklist
      ? pickTaggedLines(section.checklist, lang).map(interpolateManualHomeTokens)
      : undefined,
  };
}

/** Pick lines tagged with SK:/EN: prefixes inside mixed manual sections. */
function pickTaggedLines(lines: string[], lang: UiLanguage): string[] {
  const prefix = lang === "sk" ? "SK:" : "EN:";
  const other = lang === "sk" ? "EN:" : "SK:";
  const tagged = lines.filter((line) => line.startsWith(prefix));
  if (tagged.length > 0) {
    return tagged.map((line) => line.slice(prefix.length).trim());
  }
  if (lines.some((line) => line.startsWith(other))) {
    return [];
  }
  return lines;
}

const MANUAL_SECTIONS_EN: ManualSection[] = [
  {
    id: "quick-start",
    title: "1. Quick Start",
    paragraphs: [
      "After login, start on {HOME_LABEL}, verify app health, then launch new sessions.",
      "Run your first Supervisor flow via Agents with a single goal, constraints, and a clear done definition.",
    ],
    checklist: [
      "Sign in via /login and confirm you land on {HOME_ROUTE}.",
      "Open Agents and start a Supervisor session with one goal.",
      "Create a related task in Tasks so outcomes stay tracked.",
      "Review existing outputs in Knowledge (retrieval-first).",
      "For incidents, open Ballroom and coordinate decisions in realtime.",
    ],
  },
  {
    id: "main-sections",
    title: "2. Main sections",
    paragraphs: [
      "{HOME_LABEL} is the command center; Agents runs Supervisor sessions; Tasks covers execution and routines; Knowledge holds context and outputs; Integrations manages connectors; Ballroom is the realtime ops lane.",
      "Foragers manages data collectors (YouTube/RSS/API), schedules, HiveMind ingest, and agent spawn from forager config.",
      "Settings holds security, team, billing, and integration configuration for the tenant.",
    ],
  },
  {
    id: "best-practices",
    title: "3. Best practices",
    paragraphs: [
      "Write prompts as Goal → Context → Constraints → Done.",
      "Search Knowledge before running new compute — saves tokens and time.",
      "Use routines only for repeatable processes; start with conservative frequency.",
    ],
  },
  {
    id: "scenarios",
    title: "4. Common scenarios",
    paragraphs: [
      "Morning check: {HOME_LABEL} → Agents needs_input → Tasks priority → Integrations status → Knowledge latest outputs.",
      "Production incident: confirm symptom, start Supervisor session, coordinate in Ballroom, write conclusion to Knowledge.",
    ],
  },
  {
    id: "troubleshooting",
    title: "5. Troubleshooting",
    paragraphs: [
      "Redirect to login often means expired session cookie or missing auth token.",
      "401 is authentication; 403 is RBAC/permission guard; 404 is often route/proxy drift.",
      "For routine failures check active flag, interval, worker/beat health, and last error detail.",
    ],
  },
  {
    id: "voice-providers",
    title: "6. Voice providers (SK/EN)",
    paragraphs: pickTaggedLines(APP_MANUAL_SECTIONS.find((s) => s.id === "voice-providers")?.paragraphs ?? [], "en"),
    checklist: pickTaggedLines(APP_MANUAL_SECTIONS.find((s) => s.id === "voice-providers")?.checklist ?? [], "en"),
  },
];

const FUNCTION_DESCRIPTIONS_EN: Record<string, { description: string; options: string[] }> = {
  "dashboard-overview": {
    description: "Realtime swarm status, health signals, and active flows.",
    options: ["Open swarms/costs/monitoring details", "Quick orientation before action"],
  },
  "dashboard-monitoring": {
    description: "Host pressure, queues, and telemetry diagnostics.",
    options: ["Track performance drift", "Review incident signals"],
  },
  "agents-session": {
    description: "Supervisor session lifecycle: running, needs_input, completed.",
    options: ["Approve/Reject steps", "Review session output", "Follow-up instructions"],
  },
  "agents-spawn": {
    description: "Create a new agent within swarm orchestration.",
    options: ["Define role", "Assign swarm lane", "Initial settings"],
  },
  "agents-foragers": {
    description: "Dynamic ingest workers wired to routines, HiveMind, and spawn flow.",
    options: ["Forager CRUD", "Source/filter config", "Manual ingest and agent spawn"],
  },
  "tasks-new": {
    description: "Create a new task for the execution pipeline.",
    options: ["Priority", "Goal description", "Link to workflow/session"],
  },
  "tasks-routines": {
    description: "Scheduled automated task flows.",
    options: ["Interval/schedule", "Enable/disable", "Last run review"],
  },
  "knowledge-hivemind": {
    description: "Search existing context and historical outputs.",
    options: ["Topic filter", "Reuse prior solutions"],
  },
  "knowledge-outputs": {
    description: "Archive and reuse delivered outputs.",
    options: ["Quality review", "Link to follow-up tasks"],
  },
  "knowledge-dreaming": {
    description: "Auto-consolidate lessons from supervisor sessions into HiveMind.",
    options: ["Enable/disable", "Frequency", "Manual trigger + Dream Reports"],
  },
  "integrations-connectors": {
    description: "Manage connectors, auth state, and connection tests.",
    options: ["Connector create/update", "Connection test", "Vault sync"],
  },
  "integrations-marketplace": {
    description: "Install API tools and expose them to supervisor lanes.",
    options: ["One-click install", "Tool catalog browse"],
  },
  "ballroom-realtime": {
    description: "Live coordination during incidents and critical deploy flows.",
    options: ["Fast ops lane", "Link to Supervisor sessions"],
  },
  "settings-security": {
    description: "2FA, auth guards, and account security rules.",
    options: ["TOTP setup", "Session security", "Auth preference"],
  },
  "settings-team": {
    description: "Role-based access control for tenant members.",
    options: ["Role assignment", "Permission governance", "Access revocation"],
  },
  "settings-billing": {
    description: "Budgets, usage signals, and cost limits.",
    options: ["Spend tracking", "Budget alerts", "Usage review"],
  },
  "settings-voice-providers": {
    description: "Manage LLM/STT/TTS API keys and explicit voice pipeline provider priority.",
    options: ["Grok/Deepgram/OpenAI for STT", "Grok/ElevenLabs/OpenAI for TTS", "Auto fallback on outage"],
  },
  "cockpit-overview": {
    description: "Daily command surface — prioritized actions, Oracle warnings, Trust Autopilot, Proof-of-Hive.",
    options: ["Start day (trio cycle)", "Refresh core snapshot", "Factory / Swarms / Agents shortcuts"],
  },
  "cockpit-command": {
    description: "Hotline, Intent Crystallizer, and Zero-UI Telegram command entry points.",
    options: ["Natural language routing", "Crystallizer preview/launch", "Telegram webhook setup"],
  },
  "bee-hotline": {
    description: "Plain-language operator request routed to the correct bee and Queen goal.",
    options: ["One-sentence intent", "POST /operator/act hotline", "No panel hunting"],
  },
  "intent-crystallizer": {
    description: "Structured plan from free text: templates, trust lane, deep links.",
    options: ["Preview before launch", "Trust lane selection", "Queen goal creation"],
  },
  "zero-ui-hive": {
    description: "Telegram commands mirror Agentic OS when bot token and webhook are configured.",
    options: ["/day /status /hotline", "Execution Studio notifications", "HTTPS webhook URL"],
  },
  "icm-tools": {
    description: "Link drop, dialogue extract, and quick automations for intent capture.",
    options: ["URL brief ingest", "Transcript → harness/knowledge/recipe", "Verified presets"],
  },
  "swarm-fleet": {
    description: "Always-on routines with pause/resume and immune system status.",
    options: ["Pause/resume", "Autopilot schedules", "Watch/quarantine signals"],
  },
  "cockpit-modules": {
    description: "Lazy-loaded futurist modules composed from existing subsystems.",
    options: ["Regret simulator", "Context teleport", "Evolutionary recipes"],
  },
  "innovation-lab": {
    description: "Brainstorm features; Maintainer implements approved ideas via PR only.",
    options: ["Brainstorm", "Approve/reject", "Queue Maintainer"],
  },
};

export function manualSubtitle(lang: UiLanguage): string {
  void lang;
  return MANUAL_SUBTITLE.en;
}

export function manualSections(lang: UiLanguage): ManualSection[] {
  void lang;
  return MANUAL_SECTIONS_EN.map((section) => localizeManualSection(section, "en"));
}

export function functionGuideGroups(lang: UiLanguage): FunctionInfoGroup[] {
  void lang;
  return APP_FUNCTION_GUIDE.map((group) => ({
    ...group,
    items: group.items.map((item) => {
      const en = FUNCTION_DESCRIPTIONS_EN[item.id];
      if (!en) {
        return item;
      }
      return { ...item, description: en.description, options: en.options };
    }),
  }));
}

export function functionGuideIntro(lang: UiLanguage): string {
  void lang;
  return FUNCTION_GUIDE_INTRO.en;
}

export function functionGuideHeading(lang: UiLanguage): string {
  void lang;
  return FUNCTION_GUIDE_HEADING.en;
}
