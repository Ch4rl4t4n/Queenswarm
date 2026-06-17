import { describe, expect, it } from "vitest";

import {
  cockpitNavSections,
  SOLO_COCKPIT_ADVANCED_SECTIONS,
  SOLO_COCKPIT_HIDDEN_SECTIONS,
  SOLO_COCKPIT_PRIMARY_SECTIONS,
  visibleCockpitSections,
} from "@/lib/operator-canonical-ui";
import type { CockpitSection } from "@/lib/cockpit-routes";

const ALL: CockpitSection[] = [
  "overview",
  "business",
  "lanes",
  "command",
  "grok",
  "icm",
  "fleet",
  "modules",
  "innovation",
];

describe("operator-canonical-ui", () => {
  it("visibleCockpitSections_hides_fleet_in_solo", () => {
    const visible = visibleCockpitSections(true, ALL);
    expect(visible).not.toContain("fleet");
    expect(SOLO_COCKPIT_HIDDEN_SECTIONS).toContain("fleet");
  });

  it("visibleCockpitSections_keeps_fleet_outside_solo", () => {
    const visible = visibleCockpitSections(false, ALL);
    expect(visible).toContain("fleet");
    expect(visible).not.toContain("business");
  });

  it("visibleCockpitSections_puts_lanes_last_in_solo", () => {
    const visible = visibleCockpitSections(true, ALL);
    expect(visible.at(-1)).toBe("lanes");
    expect(visible[0]).toBe("overview");
  });

  it("cockpitNavSections_splits_primary_and_advanced_in_solo", () => {
    const split = cockpitNavSections(true, ALL);
    expect(split.primary).toEqual(["overview", "business", "innovation"]);
    expect(split.advanced).toEqual(["command", "grok", "icm", "modules", "lanes"]);
  });

  it("cockpitNavSections_flat_outside_solo", () => {
    const split = cockpitNavSections(false, ALL);
    expect(split.primary).toEqual(ALL.filter((id) => id !== "business"));
    expect(split.advanced).toEqual([]);
  });

  it("visibleCockpitSections_hides_business_in_personal_os", () => {
    const visible = visibleCockpitSections(true, ALL, true);
    expect(visible).not.toContain("business");
    expect(visible).toContain("overview");
    expect(visible).toContain("innovation");
  });

  it("cockpitNavSections_omits_business_primary_in_personal_os", () => {
    const split = cockpitNavSections(true, ALL, true);
    expect(split.primary).not.toContain("business");
    expect(split.primary).toContain("overview");
  });
});
