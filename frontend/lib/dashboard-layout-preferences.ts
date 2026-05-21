/** Dashboard section visibility — persisted per browser (localStorage). */

export const DASHBOARD_LAYOUT_STORAGE_KEY = "queenswarm:dashboard-layout-v2";

export type DashboardSectionId =
  | "search"
  | "kpiStats"
  | "pollenCosts"
  | "ballroomParticipants"
  | "agents"
  | "queenMission"
  | "subSwarms"
  | "waggleFeed"
  | "workflows"
  | "taskQueue"
  | "performanceTier"
  | "recentTasks"
  | "agentSuggestions"
  | "spawnAgent"
  | "swarmBuilderEntry"
  | "rapidLoop"
  | "dreamingSummary"
  | "timeSaved"
  | "leadMagnets"
  | "beeBadges";

export interface DashboardSectionMeta {
  id: DashboardSectionId;
  label: { en: string; sk: string };
  description: { en: string; sk: string };
  group: DashboardSectionGroupId;
}

export type DashboardSectionGroupId = "overview" | "live" | "swarms" | "execution" | "insights" | "power";

export interface DashboardSectionGroupMeta {
  id: DashboardSectionGroupId;
  label: { en: string; sk: string };
}

/** Default layout — matches current lean dashboard; optional blocks off. */
export const DASHBOARD_LAYOUT_DEFAULTS: Record<DashboardSectionId, boolean> = {
  search: true,
  kpiStats: true,
  pollenCosts: true,
  ballroomParticipants: true,
  agents: true,
  queenMission: true,
  subSwarms: true,
  waggleFeed: false,
  workflows: false,
  taskQueue: true,
  performanceTier: true,
  recentTasks: true,
  agentSuggestions: false,
  spawnAgent: false,
  swarmBuilderEntry: true,
  rapidLoop: true,
  dreamingSummary: true,
  timeSaved: true,
  leadMagnets: true,
  beeBadges: true,
};

export const DASHBOARD_SECTION_GROUPS: DashboardSectionGroupMeta[] = [
  { id: "overview", label: { en: "Overview", sk: "Prehľad" } },
  { id: "live", label: { en: "Live hive", sk: "Live hive" } },
  { id: "swarms", label: { en: "Swarms & signals", sk: "Swarmy a signály" } },
  { id: "execution", label: { en: "Execution", sk: "Exekúcia" } },
  { id: "insights", label: { en: "Insights", sk: "Prehľady" } },
  { id: "power", label: { en: "Power user", sk: "Pokročilé" } },
];

export const DASHBOARD_SECTIONS: DashboardSectionMeta[] = [
  {
    id: "search",
    group: "overview",
    label: { en: "Agent search", sk: "Vyhľadávanie agentov" },
    description: { en: "Filter roster by tier, name, swarm", sk: "Filter rosteru podľa tieru, mena, swarmu" },
  },
  {
    id: "kpiStats",
    group: "overview",
    label: { en: "KPI tiles", sk: "KPI karty" },
    description: { en: "Agents, tasks, LLM routing", sk: "Agenti, tasky, LLM routing" },
  },
  {
    id: "pollenCosts",
    group: "overview",
    label: { en: "Pollen & costs", sk: "Pollen a náklady" },
    description: { en: "Roster activity and 30-day spend", sk: "Aktivita rosteru a spend 30 dní" },
  },
  {
    id: "agents",
    group: "live",
    label: { en: "Agents", sk: "Agenti" },
    description: { en: "Hex grid / list with filters", sk: "Hex mriežka / zoznam s filtrami" },
  },
  {
    id: "ballroomParticipants",
    group: "live",
    label: { en: "Ballroom · live", sk: "Ballroom · live" },
    description: { en: "Live participants strip", sk: "Pás live účastníkov" },
  },
  {
    id: "queenMission",
    group: "live",
    label: { en: "Queen mission", sk: "Queen mission" },
    description: { en: "Brief + run 7-step flow", sk: "Brief + spustenie 7-krokového flow" },
  },
  {
    id: "subSwarms",
    group: "swarms",
    label: { en: "Sub-swarms", sk: "Sub-swarms" },
    description: { en: "Decentralized swarm cards", sk: "Karty decentralizovaných swarmov" },
  },
  {
    id: "waggleFeed",
    group: "swarms",
    label: { en: "Waggle dance feed", sk: "Waggle dance feed" },
    description: { en: "Cross-swarm handoff signals", sk: "Signály medzi swarmami" },
  },
  {
    id: "taskQueue",
    group: "execution",
    label: { en: "Task queue", sk: "Task queue" },
    description: { en: "Running, queued, and done tasks", sk: "Bežiace, vo fronte a hotové tasky" },
  },
  {
    id: "workflows",
    group: "execution",
    label: { en: "Workflows", sk: "Workflows" },
    description: { en: "DAG executions from tasks", sk: "DAG exekúcie z taskov" },
  },
  {
    id: "performanceTier",
    group: "insights",
    label: { en: "Performance by tier", sk: "Výkon podľa tieru" },
    description: { en: "Share of agents in the hive", sk: "Podiel agentov v hive" },
  },
  {
    id: "recentTasks",
    group: "insights",
    label: { en: "Recent tasks", sk: "Posledné tasky" },
    description: { en: "Latest rows from /api/v1/tasks", sk: "Posledné riadky z /api/v1/tasks" },
  },
  {
    id: "agentSuggestions",
    group: "insights",
    label: { en: "Agent suggestions", sk: "Návrhy agentov" },
    description: { en: "Reflection-cycle proposals", sk: "Návrhy z reflection cyklov" },
  },
  {
    id: "spawnAgent",
    group: "power",
    label: { en: "Spawn agent (advanced)", sk: "Spawn agent (advanced)" },
    description: { en: "Quick manager/worker create form", sk: "Rýchly formulár manager/worker" },
  },
  {
    id: "swarmBuilderEntry",
    group: "overview",
    label: { en: "Swarm Builder CTA", sk: "Swarm Builder CTA" },
    description: { en: "Hero path to opinionated swarm templates", sk: "Vstup do opinionated swarm šablón" },
  },
  {
    id: "rapidLoop",
    group: "insights",
    label: { en: "Rapid learning loop", sk: "Rapid learning loop" },
    description: { en: "Scrape → reflect → simulate → reward SLA", sk: "SLA cyklu scrape → reflect → simulate → reward" },
  },
  {
    id: "dreamingSummary",
    group: "insights",
    label: { en: "Dreaming summary", sk: "Dreaming prehľad" },
    description: { en: "Latest nightly memory consolidation", sk: "Posledný nočný memory cyklus" },
  },
  {
    id: "timeSaved",
    group: "insights",
    label: { en: "Time saved ROI", sk: "Ušetrený čas" },
    description: { en: "Verified workflow hours saved by template", sk: "Ušetrené hodiny podľa šablón" },
  },
  {
    id: "leadMagnets",
    group: "overview",
    label: { en: "Lead magnets", sk: "Lead magnety" },
    description: { en: "Share cards + public landing for swarm templates", sk: "Share karty + verejný landing pre šablóny" },
  },
  {
    id: "beeBadges",
    group: "insights",
    label: { en: "Bee badges", sk: "Bee odznaky" },
    description: { en: "Verified-workflow gamification badges", sk: "Gamifikácia overených workflow" },
  },
];

export type DashboardLayoutPreferences = Record<DashboardSectionId, boolean>;

function resolveBrowserStorage(): Storage | null {
  try {
    if (typeof window === "undefined") {
      return null;
    }
    return window.localStorage;
  } catch {
    return null;
  }
}

export function mergeDashboardLayout(raw: Partial<DashboardLayoutPreferences> | null | undefined): DashboardLayoutPreferences {
  return { ...DASHBOARD_LAYOUT_DEFAULTS, ...raw };
}

export function readStoredDashboardLayout(storage: Pick<Storage, "getItem"> | null | undefined): DashboardLayoutPreferences {
  if (!storage) {
    return { ...DASHBOARD_LAYOUT_DEFAULTS };
  }
  try {
    const raw = storage.getItem(DASHBOARD_LAYOUT_STORAGE_KEY);
    if (!raw) {
      return { ...DASHBOARD_LAYOUT_DEFAULTS };
    }
    const parsed = JSON.parse(raw) as Partial<DashboardLayoutPreferences>;
    return mergeDashboardLayout(parsed);
  } catch {
    return { ...DASHBOARD_LAYOUT_DEFAULTS };
  }
}

export function saveStoredDashboardLayout(
  storage: Pick<Storage, "setItem"> | null | undefined,
  layout: DashboardLayoutPreferences,
): void {
  if (!storage) {
    return;
  }
  try {
    storage.setItem(DASHBOARD_LAYOUT_STORAGE_KEY, JSON.stringify(layout));
  } catch {
    // Ignore blocked storage.
  }
}

export function readStoredDashboardLayoutFromBrowser(): DashboardLayoutPreferences {
  return readStoredDashboardLayout(resolveBrowserStorage());
}

export function saveStoredDashboardLayoutFromBrowser(layout: DashboardLayoutPreferences): void {
  saveStoredDashboardLayout(resolveBrowserStorage(), layout);
}
