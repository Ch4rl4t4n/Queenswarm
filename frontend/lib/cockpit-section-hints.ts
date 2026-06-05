/** @deprecated Import from `@/lib/section-hints` — kept for cockpit panel imports. */

import { sectionHintProps, type SectionHint, type SectionHintKey } from "@/lib/section-hints";

export type CockpitSectionHint = SectionHint;

export type CockpitHintKey = Extract<
  SectionHintKey,
  | "overview"
  | "businessOperator"
  | "fourLanes"
  | "command"
  | "beeHotline"
  | "intentCrystallizer"
  | "zeroUi"
  | "icm"
  | "fleet"
  | "modules"
  | "innovation"
>;

export function cockpitHintProps(key: CockpitHintKey): CockpitSectionHint {
  return sectionHintProps(key);
}
