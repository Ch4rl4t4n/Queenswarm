import { describe, expect, it } from "vitest";

import {
  CAPABILITIES_DENSITY_SECTIONS,
  HARNESS_LOOPS_PANEL_SPECS,
  harnessLoopsPanelSpec,
  settingsDensityAdvancedSectionIds,
  settingsDensityEssentialSectionIds,
} from "@/lib/settings-panel-density";

describe("settings-panel-density", () => {
  it("capabilities keeps live catalog essential and atlas sections advanced", () => {
    const essential = settingsDensityEssentialSectionIds(CAPABILITIES_DENSITY_SECTIONS);
    const advanced = settingsDensityAdvancedSectionIds(CAPABILITIES_DENSITY_SECTIONS);

    expect(essential).toContain("capabilities-live");
    expect(advanced).toContain("capabilities-architecture");
    expect(advanced).toContain("capabilities-roadmap");
    expect(advanced).toContain("capabilities-mission");
  });

  it("harness loops exposes only trio as essential default-open", () => {
    const essential = HARNESS_LOOPS_PANEL_SPECS.filter((row) => row.tier === "essential");
    expect(essential).toHaveLength(1);
    expect(essential[0]?.id).toBe("harness-loops-trio");
    expect(essential[0]?.defaultOpen).toBe(true);
  });

  it("resolves harness loop panel spec by id", () => {
    expect(harnessLoopsPanelSpec("harness-loops-forager")?.title).toBe("Forager intelligence loop");
    expect(harnessLoopsPanelSpec("missing")).toBeUndefined();
  });
});
