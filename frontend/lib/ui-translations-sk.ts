export const UI_TRANSLATIONS_SK: Record<string, string> = {
  // Core navigation + shell
  Dashboard: "Nástenka",
  Agents: "Agenti",
  Tasks: "Úlohy",
  Knowledge: "Znalosti",
  Integrations: "Integrácie",
  Ballroom: "Ballroom",
  Settings: "Nastavenia",
  Manual: "Manuál",
  More: "Viac",
  "Hive navigation": "Hive navigácia",
  Session: "Relácia",
  "Log out": "Odhlásiť",
  out: "odhlásiť",
  "Open navigation menu": "Otvoriť navigáciu",
  "Close menu": "Zavrieť menu",
  "Close sheet": "Zavrieť panel",
  Notifications: "Notifikácie",
  "Hive alerts": "Hive upozornenia",
  "Nothing unread.": "Nič neprečítané.",
  today: "dnes",
  "HIVE ONLINE": "HIVE ONLINE",
  "Search agents, tasks, workflows...": "Hľadaj agentov, úlohy, workflowy...",
  "Search agents, tasks, workflows": "Hľadaj agentov, úlohy, workflowy",
  Search: "Hľadať",
  "Hive search": "Hive vyhľadávanie",
  "Session cleared": "Relácia vyčistená",
  "Logged out": "Odhlásené",
  "Login screen": "Prihlasovacia obrazovka",
  "Shortcuts · desktop": "Skratky · desktop",
  "Go to dashboard": "Prejsť na nástenku",
  "Voice + transcript": "Hlas + prepis",
  "syncing hive…": "synchronizujem hive…",
  "hive warming…": "hive sa zahrieva…",

  // Settings
  "Security · 2FA": "Bezpečnosť · 2FA",
  "Billing · Usage": "Billing · Usage",
  "Team · RBAC": "Tím · RBAC",
  "Public sharing": "Verejné zdieľanie",
  "LLM keys": "LLM kľúče",
  "API keys · external": "API kľúče · externé",
  Language: "Jazyk",

  // Common actions
  "Open Ballroom": "Otvoriť Ballroom",
  "Open manual": "Otvoriť manuál",
  "Start session": "Spustiť reláciu",
  "End session": "Ukončiť reláciu",
  "Reconnect stream": "Znovu pripojiť stream",
  Send: "Odoslať",
  "Send →": "Odoslať →",
  "New task": "Nová úloha",
  "Create session": "Vytvoriť reláciu",
  "Create routine": "Vytvoriť rutinu",
  "Run now": "Spustiť teraz",
  Pause: "Pozastaviť",
  Resume: "Obnoviť",
  Stop: "Zastaviť",
  Approve: "Schváliť",
  Reject: "Zamietnuť",
  Retry: "Skúsiť znova",
  "Retry fetch": "Skúsiť fetch znova",

  // Dashboard / section cards
  "Live dashboard": "Live nástenka",
  Swarms: "Rojy",
  Costs: "Náklady",
  Monitoring: "Monitoring",
  "System status": "Stav systému",
  "Live infra snapshot for swarm operators — adaptive polling via cookie JWT.":
    "Live infra snapshot pre swarm operátorov — adaptívny polling cez cookie JWT.",
  "Overview · monitoring · costs": "Prehľad · monitoring · náklady",
  "Primary command deck for overview, monitoring, costs, and live swarm health.":
    "Hlavný command deck pre prehľad, monitoring, náklady a live zdravie roju.",

  // Ballroom
  "Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration.":
    "Realtime hlasová + chat lane integrovaná so supervisor sessions a live orchestráciou roju.",
  "Voice chat mode": "Režim hlasového chatu",
  "Live transcript will appear here.": "Live prepis sa zobrazí tu.",
  Participants: "Účastníci",
  "LIVE STREAM": "LIVE STREAM",
  "CHAT READY · STREAM CONNECTING": "CHAT READY · STREAM SA PRIPÁJA",
  listening: "počúva",
  "speaking…": "hovorí…",
  "stream reconnecting…": "stream sa znovu pripája…",
  offline: "offline",
  "Waiting for ballroom…": "Čakám na ballroom…",
  "Opening channel…": "Otváram kanál…",
  "Send message to the swarm…": "Pošli správu roju…",

  // Tasks
  "Task status filter": "Filter stavu úloh",
  "Task search": "Vyhľadávanie úloh",
  "No tasks in this filter.": "Žiadne úlohy v tomto filtri.",
  Progress: "Priebeh",
  Running: "Bežiace",
  Pending: "Čakajúce",
  Completed: "Dokončené",
  All: "Všetky",

  // Knowledge / HiveMind
  "Knowledge command center": "Knowledge command centrum",
  "Knowledge filter": "Knowledge filter",
  "HiveMind Galaxy": "HiveMind Galaxy",
  "Embedding hits": "Embedding hity",
  "Deliverable prism": "Deliverable prism",
  "Recall appendix preview": "Recall appendix preview",
  "Refresh graph": "Obnoviť graph",
  "Export ZIP": "Export ZIP",
  "Warping constellation…": "Renderujem konšteláciu…",

  // Hints generic
  "Configuration options": "Možnosti nastavenia",
  "Open section": "Otvoriť sekciu",
  "Review details": "Skontrolovať detaily",
  "Execute action": "Vykonať akciu",
};

export function translateUiText(value: string, lang: "en" | "sk"): string {
  if (lang !== "sk") {
    return value;
  }
  const direct = UI_TRANSLATIONS_SK[value];
  if (direct) {
    return direct;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return value;
  }
  const trimmedMapped = UI_TRANSLATIONS_SK[trimmed];
  if (!trimmedMapped) {
    return value;
  }
  const start = value.indexOf(trimmed);
  if (start < 0) {
    return trimmedMapped;
  }
  const end = start + trimmed.length;
  return `${value.slice(0, start)}${trimmedMapped}${value.slice(end)}`;
}
