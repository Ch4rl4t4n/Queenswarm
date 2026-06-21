/** @deprecated Import from `@/lib/section-hints` — kept for HivePageHeader imports. */

import { sectionHintProps, type SectionHint, type SectionHintKey } from "@/lib/section-hints";

export type HivePageHint = SectionHint;

export type HivePageHintKey =
  | Extract<
      SectionHintKey,
      | "settings"
      | "knowledge"
      | "cockpit"
      | "appsTools"
      | "agents"
      | "integrations"
      | "ballroom"
      | "swarms"
      | "factory"
      | "skillFactory"
      | "tasks"
      | "routines"
      | "dashboard"
      | "manual"
      | "foragers"
      | "monitoring"
    >
  | "workflows";

export const HIVE_PAGE_HINTS = {
  settings: sectionHintProps("settings"),
  knowledge: sectionHintProps("knowledge"),
  cockpit: sectionHintProps("cockpit"),
  appsTools: sectionHintProps("appsTools"),
  agents: sectionHintProps("agents"),
  integrations: sectionHintProps("integrations"),
  ballroom: sectionHintProps("ballroom"),
  swarms: sectionHintProps("swarms"),
  factory: sectionHintProps("factory"),
  skillFactory: sectionHintProps("skillFactory"),
  tasks: sectionHintProps("tasks"),
  routines: sectionHintProps("routines"),
  workflows: sectionHintProps("agentsWorkflows"),
  dashboard: sectionHintProps("dashboard"),
  manual: sectionHintProps("manual"),
  foragers: sectionHintProps("foragers"),
  monitoring: sectionHintProps("monitoring"),
} as const;

export function hivePageHintProps(key: HivePageHintKey): HivePageHint {
  if (key === "workflows") {
    return sectionHintProps("agentsWorkflows");
  }
  return sectionHintProps(key);
}
