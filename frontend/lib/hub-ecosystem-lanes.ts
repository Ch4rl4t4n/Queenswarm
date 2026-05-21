/** Cross-hub ecosystem shortcut presets for consolidated Phase 7.0 navigation. */

import type { LucideIcon } from "lucide-react";
import { Brain, ListTodo, Mic, Plug, Users } from "lucide-react";

import { integrationsTabHref } from "@/lib/integrations-routes";
import { knowledgeTabHref } from "@/lib/knowledge-routes";

export type HubEcosystemPreset =
  | "ballroom"
  | "agents"
  | "tasks"
  | "knowledge"
  | "dashboard"
  | "integrations";

export interface HubEcosystemLane {
  label: string;
  href: string;
  icon: LucideIcon;
}

const AGENTS: HubEcosystemLane = {
  label: "Agents",
  href: "/agents",
  icon: Users,
};

const INTEGRATIONS: HubEcosystemLane = {
  label: "Integrations",
  href: integrationsTabHref("active", "ecosystem"),
  icon: Plug,
};

const SUPERVISOR: HubEcosystemLane = {
  label: "Supervisor",
  href: "/agents#sessions",
  icon: Users,
};

const HIVEMIND: HubEcosystemLane = {
  label: "HiveMind",
  href: knowledgeTabHref("hivemind"),
  icon: Brain,
};

const TASKS: HubEcosystemLane = {
  label: "Tasks",
  href: "/tasks",
  icon: ListTodo,
};

const BALLROOM: HubEcosystemLane = {
  label: "Ballroom",
  href: "/ballroom",
  icon: Mic,
};

/** Resolve ecosystem cross-links for a consolidated hub page. */
export function hubEcosystemLanes(preset: HubEcosystemPreset): readonly HubEcosystemLane[] {
  switch (preset) {
    case "ballroom":
      return [INTEGRATIONS, SUPERVISOR, HIVEMIND];
    case "agents":
      return [INTEGRATIONS, HIVEMIND, BALLROOM, TASKS];
    case "tasks":
      return [INTEGRATIONS, SUPERVISOR, BALLROOM, HIVEMIND];
    case "knowledge":
      return [INTEGRATIONS, SUPERVISOR, BALLROOM, TASKS];
    case "dashboard":
      return [AGENTS, TASKS, INTEGRATIONS, BALLROOM];
    case "integrations":
      return [SUPERVISOR, TASKS, HIVEMIND, BALLROOM];
    default: {
      const _exhaustive: never = preset;
      return _exhaustive;
    }
  }
}
