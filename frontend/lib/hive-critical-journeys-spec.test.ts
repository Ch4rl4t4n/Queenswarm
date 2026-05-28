import { describe, expect, it } from "vitest";

import { CANONICAL_PRIMARY_CP_HREFS } from "@/lib/hive-ia-canonical";
import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";
import {
  canonicalAgenticOsLabels,
  criticalJourneyMoreMenuCoverage,
  criticalJourneyPrimaryRouteCoverage,
  HIVE_CRITICAL_JOURNEY_SPECS,
  hiveCriticalJourneyCount,
} from "@/lib/hive-critical-journeys-spec";

describe("hive-critical-journeys-spec", () => {
  it("defines unique journey ids", () => {
    const ids = HIVE_CRITICAL_JOURNEY_SPECS.map((row) => row.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(hiveCriticalJourneyCount()).toBeGreaterThanOrEqual(8);
  });

  it("covers all hive page zone specs in journey matrix", () => {
    const zonePaths = new Set(HIVE_PAGE_ZONE_SPECS.map((spec) => spec.path));
    const journeyPaths = new Set([
      ...HIVE_PAGE_ZONE_SPECS.map((spec) => spec.path),
      "/tasks/new",
      "/settings/api-keys",
      "/apps-tools/marketing-automation",
      "/foragers",
    ]);
    for (const path of zonePaths) {
      expect(journeyPaths.has(path), `missing journey coverage for ${path}`).toBe(true);
    }
  });

  it("maps agentic os labels from canonical IA", () => {
    const labels = canonicalAgenticOsLabels();
    expect(labels).toContain("Agentic OS");
    expect(labels).toContain("Swarms");
    expect(labels).toContain("Tasks");
    expect(labels).toContain("Agents");
  });

  it("tracks verified primary routes touched by journeys", () => {
    const covered = criticalJourneyPrimaryRouteCoverage();
    expect(covered.length).toBeGreaterThanOrEqual(CANONICAL_PRIMARY_CP_HREFS.length - 1);
    expect(covered).toContain("/agentic-os");
    expect(covered).toContain("/knowledge");
  });

  it("includes foragers in more-menu coverage", () => {
    expect(criticalJourneyMoreMenuCoverage()).toContain("/foragers");
  });
});
