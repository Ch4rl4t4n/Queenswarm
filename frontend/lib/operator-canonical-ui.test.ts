import { describe, expect, it } from "vitest";

import {
  cockpitNavSections,
  SOLO_COCKPIT_HIDDEN_SECTIONS,
  visibleCockpitSections,
} from "@/lib/operator-canonical-ui";
import type { CockpitSection } from "@/lib/cockpit-routes";

const ALL: CockpitSection[] = [
  "business",
  "overview",
  "lanes",
  "command",
  "grok",
  "icm",
  "fleet",
  "modules",
  "innovation",
];

describe("operator-canonical-ui", () => {
  it("visibleCockpitSections_shows_all_tabs_in_solo", () => {
    const visible = visibleCockpitSections(true, ALL);
    expect(visible).toHaveLength(ALL.length);
    expect(visible).toContain("business");
    expect(visible).toContain("fleet");
    expect(SOLO_COCKPIT_HIDDEN_SECTIONS).toHaveLength(0);
  });

  it("visibleCockpitSections_hides_business_outside_solo", () => {
    const visible = visibleCockpitSections(false, ALL);
    expect(visible).not.toContain("business");
    expect(visible).toContain("overview");
  });

  it("visibleCockpitSections_keeps_fleet_outside_solo", () => {
    const visible = visibleCockpitSections(false, ALL);
    expect(visible).toContain("fleet");
  });

  it("visibleCockpitSections_puts_lanes_last_in_solo", () => {
    const visible = visibleCockpitSections(true, ALL);
    expect(visible.at(-1)).toBe("lanes");
    expect(visible[0]).toBe("business");
  });

  it("cockpitNavSections_splits_primary_and_secondary_rows_in_solo", () => {
    const split = cockpitNavSections(true, ALL);
    expect(split.primary).toEqual(["business", "overview", "innovation"]);
    expect(split.advanced).toEqual(["command", "grok", "icm", "modules", "fleet", "lanes"]);
  });

  it("cockpitNavSections_flat_outside_solo", () => {
    const split = cockpitNavSections(false, ALL);
    expect(split.primary).toEqual(ALL.filter((id) => id !== "business"));
    expect(split.advanced).toEqual([]);
  });
});
