export interface DesktopShortcutTargets {
  home: string;
  tasks: string;
  knowledge: string;
  integrations: string;
}

export type HubSection = "overview" | "execution" | "knowledge" | "integrations";

export function shortcutTargets(consolidatedEnabled: boolean): DesktopShortcutTargets {
  if (consolidatedEnabled) {
    return {
      home: "/dashboard",
      tasks: "/tasks",
      knowledge: "/knowledge",
      integrations: "/integrations",
    };
  }
  return {
    home: "/",
    tasks: "/tasks",
    knowledge: "/hive-mind",
    integrations: "/connectors",
  };
}

export function keyboardLegendText(consolidatedEnabled: boolean): string {
  if (consolidatedEnabled) {
    return "QueenSwarm · consolidated cockpit · Alt+H dashboard · Alt+T tasks · Alt+B ballroom · Alt+O knowledge · Alt+M integrations";
  }
  return "QueenSwarm · classic cockpit · Alt+H dashboard · Alt+T tasks · Alt+B ballroom · Alt+O HiveMind · Alt+M connectors";
}

export function hubFallbackTarget(section: HubSection): string {
  if (section === "overview") {
    return "/";
  }
  if (section === "execution") {
    return "/tasks";
  }
  if (section === "knowledge") {
    return "/hive-mind";
  }
  return "/connectors";
}
