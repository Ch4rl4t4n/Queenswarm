import { describe, expect, it } from "vitest";

import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";
import {
  HIVE_PROD_JOURNEY_ROUTES,
  HIVE_PROD_JOURNEY_ZONE_ROUTES,
  hiveProdJourneyRouteCount,
} from "@/lib/hive-prod-journey-spec";

describe("hive-prod-journey-spec", () => {
  it("covers all zone specs", () => {
    const zonePaths = new Set(HIVE_PROD_JOURNEY_ZONE_ROUTES.map((row) => row.path));
    for (const spec of HIVE_PAGE_ZONE_SPECS) {
      expect(zonePaths.has(spec.path), `missing prod route for ${spec.path}`).toBe(true);
    }
  });

  it("includes settings and apps-tools secondary routes", () => {
    const paths = HIVE_PROD_JOURNEY_ROUTES.map((row) => row.path);
    expect(paths).toContain("/settings/security");
    expect(paths).toContain("/apps-tools/marketing-automation");
    expect(paths).toContain("/tasks/new");
  });

  it("exports stable route count", () => {
    expect(hiveProdJourneyRouteCount()).toBe(HIVE_PROD_JOURNEY_ROUTES.length);
    expect(hiveProdJourneyRouteCount()).toBeGreaterThanOrEqual(HIVE_PAGE_ZONE_SPECS.length + 3);
  });
});
