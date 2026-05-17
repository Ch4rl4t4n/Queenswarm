import type { UiLanguage } from "@/lib/ui-language";
import { translateUiText } from "@/lib/ui-translations-sk";

const NAV_LABEL_SK: Record<string, string> = {
  Overview: "Prehľad",
  Execution: "Exekúcia",
  Dashboard: "Nástenka",
  Agents: "Agenti",
  Tasks: "Úlohy",
  Knowledge: "Znalosti",
  Integrations: "Integrácie",
  Ballroom: "Ballroom",
  Settings: "Nastavenia",
  Manual: "Manuál",
  "Live dashboard": "Live nástenka",
  Swarms: "Rojy",
  Costs: "Náklady",
  Monitoring: "Monitoring",
  "Live network": "Live sieť",
  "Dashboard hub": "Nástenka hub",
  "Agents hub": "Agenti hub",
  "Tasks hub": "Úlohy hub",
  "Knowledge hub": "Znalosti hub",
  "Integrations hub": "Integrácie hub",
  Connectors: "Konektory",
  Outputs: "Výstupy",
  Learning: "Učenie",
  Recipes: "Recepty",
  Leaderboard: "Rebríček",
  "External apps": "Externé aplikácie",
  Plugins: "Pluginy",
  "Realtime Ballroom": "Realtime Ballroom",
  "New task": "Nová úloha",
  "Spawn agent": "Spawn agent",
  Hierarchy: "Hierarchia",
  Workflows: "Workflowy",
  "Async jobs": "Async úlohy",
  Simulations: "Simulácie",
  HiveMind: "HiveMind",
};

export function localizeNavLabel(label: string, language: UiLanguage): string {
  if (language !== "sk") {
    return label;
  }
  return NAV_LABEL_SK[label] ?? label;
}

export function localizePhrase(
  language: UiLanguage,
  copy: { en: string; sk: string },
): string {
  return language === "sk" ? copy.sk : copy.en;
}

export function localizeText(text: string, language: UiLanguage): string {
  return translateUiText(text, language);
}
