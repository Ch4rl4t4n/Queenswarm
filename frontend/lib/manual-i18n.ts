import type { FunctionInfoGroup, ManualSection } from "@/lib/manual-content";
import { APP_FUNCTION_GUIDE, APP_MANUAL_SECTIONS } from "@/lib/manual-content";
import { hiveOverviewHref, hiveOverviewLabel } from "@/lib/hive-home-route";
import { MANUAL_FUNCTION_HREFS } from "@/lib/manual-routes";
import type { UiLanguage } from "@/lib/ui-language";

const MANUAL_SUBTITLE: Record<UiLanguage, string> = {
  en: "Single canonical workflow first — then optional automation. Full doc: docs/OPERATOR_CANONICAL_WORKFLOW.md",
  sk: "Single canonical workflow first — then optional automation. Full doc: docs/OPERATOR_CANONICAL_WORKFLOW.md",
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

const FUNCTION_DESCRIPTIONS_EN: Record<string, { description: string; options: string[] }> = {
  "canonical-session": {
    description: "Primary path: structured PROJECT goal, durable runtime, Create → Info report → Tasks or phase 2.",
    options: ["Goal → Context → Constraints → Done", "One project = one session", "/manual#canonical-workflow"],
  },
  "canonical-knowledge": {
    description: "Project briefs before first session — Queen injects into every new run.",
    options: ["instructions / mission", "PROJECT blocks", "Export .md backup"],
  },
  "canonical-tasks": {
    description: "Track deliverables after approved reports — not how you start work.",
    options: ["Priority", "Promote from digest inbox", "Weekly review"],
  },
  "agents-session": {
    description: "Primary OS control — launch projects here, not via Swarm Builder or Agentic OS Lanes.",
    options: ["Create session", "Auto-approve ON", "Info → PDF", "durable for large projects"],
  },
  "dashboard-overview": {
    description: "Realtime swarm status, health signals, and active flows.",
    options: ["Open swarms/costs/monitoring details", "Quick orientation before action"],
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
    description: "Brainstorm features; viability gate then Maintainer implements approved ideas via PR only.",
    options: ["Brainstorm", "Approve & queue", "Viability checks", "High-risk ack"],
  },
  "harness-four-cs": {
    description: "Four Cs AI OS readiness audit in Harness overview.",
    options: ["Context score", "Connections score", "Capabilities + Cadence"],
  },
  "innovation-viability": {
    description: "Deterministic gate before Innovation Lab queues Maintainer.",
    options: ["Plan length", "Simulate trust lane", "Pre-tool denylist"],
  },
  "maintainer-safety": {
    description: "PR-only Maintainer with pre-tool denylist and daily budget.",
    options: ["No force-push", "No prod deploy", "Branch queen-maintainer/*"],
  },
};

export function manualSubtitle(lang: UiLanguage): string {
  return MANUAL_SUBTITLE[lang];
}

export function manualSections(lang: UiLanguage): ManualSection[] {
  void lang;
  return APP_MANUAL_SECTIONS.map((section) => ({
    ...section,
    paragraphs: section.paragraphs.map(interpolateManualHomeTokens),
    checklist: section.checklist?.map((item) => ({
      ...item,
      text: interpolateManualHomeTokens(item.text),
    })),
  }));
}

export function functionGuideGroups(lang: UiLanguage): FunctionInfoGroup[] {
  void lang;
  return APP_FUNCTION_GUIDE.map((group) => ({
    ...group,
    items: group.items.map((item) => {
      const en = FUNCTION_DESCRIPTIONS_EN[item.id];
      const href = MANUAL_FUNCTION_HREFS[item.id] ?? item.href;
      if (!en) {
        return href ? { ...item, href } : item;
      }
      return { ...item, description: en.description, options: en.options, href };
    }),
  }));
}

export function functionGuideIntro(lang: UiLanguage): string {
  return FUNCTION_GUIDE_INTRO[lang];
}

export function functionGuideHeading(lang: UiLanguage): string {
  return FUNCTION_GUIDE_HEADING[lang];
}
