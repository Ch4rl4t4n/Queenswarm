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
      | "tasks"
      | "routines"
      | "dashboard"
      | "manual"
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
  tasks: sectionHintProps("tasks"),
  routines: sectionHintProps("routines"),
  workflows: sectionHintProps("agentsWorkflows"),
  dashboard: sectionHintProps("dashboard"),
  manual: sectionHintProps("manual"),
} as const;

export function hivePageHintProps(key: HivePageHintKey): HivePageHint {
  if (key === "workflows") {
    return sectionHintProps("agentsWorkflows");
  }
  return sectionHintProps(key);
}
