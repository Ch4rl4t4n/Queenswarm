import { describe, expect, it } from "vitest";

import { HIVE_PAGE_HINTS } from "@/lib/hive-page-hints";
import {
  HIVE_PAGE_SHELL_VERSION,
  HIVE_PAGE_ZONE_SPECS,
  hivePageZoneSpecForPath,
} from "@/lib/hive-page-zone-spec";

describe("hive-page-zone-spec", () => {
  it("exports stable shell version", () => {
    expect(HIVE_PAGE_SHELL_VERSION).toMatch(/^2026\.\d+-v\d+$/);
  });

  it("covers all five IA zones plus agentic_os sub-routes", () => {
    const paths = HIVE_PAGE_ZONE_SPECS.map((s) => s.path);
    expect(paths).toContain("/agentic-os");
    expect(paths).toContain("/apps-tools");
    expect(paths).toContain("/integrations");
    expect(paths).toContain("/knowledge");
    expect(paths).toContain("/ballroom");
    expect(paths.filter((p) => p.startsWith("/agentic-os") || ["/swarms", "/tasks", "/routines", "/agents"].includes(p))).toHaveLength(5);
  });

  it("maps every zone spec hintKey to HIVE_PAGE_HINTS", () => {
    for (const spec of HIVE_PAGE_ZONE_SPECS) {
      expect(HIVE_PAGE_HINTS[spec.hintKey]).toBeDefined();
      expect(HIVE_PAGE_HINTS[spec.hintKey].title.length).toBeGreaterThan(0);
    }
  });

  it("resolves path lookup with trailing slash normalization", () => {
    expect(hivePageZoneSpecForPath("/apps-tools")?.title).toBe("Apps & Tools");
    expect(hivePageZoneSpecForPath("/apps-tools/")?.title).toBe("Apps & Tools");
    expect(hivePageZoneSpecForPath("/unknown")).toBeUndefined();
  });
});
