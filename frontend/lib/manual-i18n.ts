import type { FunctionInfoGroup, ManualSection } from "@/lib/manual-content";
import { APP_FUNCTION_GUIDE, APP_MANUAL_SECTIONS } from "@/lib/manual-content";
import type { UiLanguage } from "@/lib/ui-language";

const MANUAL_SUBTITLE: Record<UiLanguage, string> = {
  en: "Complete guide for operating Queenswarm — function names stay in English; prose follows your language toggle.",
  sk: "Kompletný návod na presné používanie celej aplikácie Queenswarm vrátane funkcií a možností nastavenia.",
};

const FUNCTION_GUIDE_INTRO: Record<UiLanguage, string> = {
  en: "Each function below has an Info icon with functionality notes and configuration options.",
  sk: "Každá funkcia nižšie má `Info` ikonu s popisom funkcionality a možností nastavenia.",
};

const FUNCTION_GUIDE_HEADING: Record<UiLanguage, string> = {
  en: "App functions and info descriptions",
  sk: "Funkcie aplikácie a info popisy",
};

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
      "After login, start on Dashboard, verify app health, then launch new sessions.",
      "Run your first Supervisor flow via Agents with a single goal, constraints, and a clear done definition.",
    ],
    checklist: [
      "Sign in via /login and confirm you land on /dashboard.",
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
      "Dashboard is the command center; Agents runs Supervisor sessions; Tasks covers execution and routines; Knowledge holds context and outputs; Integrations manages connectors; Ballroom is the realtime ops lane.",
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
      "Morning check: Dashboard → Agents needs_input → Tasks priority → Integrations status → Knowledge latest outputs.",
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
};

export function manualSubtitle(lang: UiLanguage): string {
  return MANUAL_SUBTITLE[lang];
}

export function manualSections(lang: UiLanguage): ManualSection[] {
  if (lang === "en") {
    return MANUAL_SECTIONS_EN;
  }
  return APP_MANUAL_SECTIONS.map((section) => ({
    ...section,
    paragraphs: pickTaggedLines(section.paragraphs, "sk"),
    checklist: section.checklist ? pickTaggedLines(section.checklist, "sk") : undefined,
  }));
}

export function functionGuideGroups(lang: UiLanguage): FunctionInfoGroup[] {
  return APP_FUNCTION_GUIDE.map((group) => ({
    ...group,
    items: group.items.map((item) => {
      if (lang === "sk") {
        return item;
      }
      const en = FUNCTION_DESCRIPTIONS_EN[item.id];
      if (!en) {
        return item;
      }
      return { ...item, description: en.description, options: en.options };
    }),
  }));
}

export function functionGuideIntro(lang: UiLanguage): string {
  return FUNCTION_GUIDE_INTRO[lang];
}

export function functionGuideHeading(lang: UiLanguage): string {
  return FUNCTION_GUIDE_HEADING[lang];
}
