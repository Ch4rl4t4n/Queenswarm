import { describe, expect, it } from "vitest";

import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";
import {
  HIVE_RELEASE_GATE_INVARIANTS,
  HIVE_RELEASE_GATE_VERSION,
  hiveReleaseGateVersionBundle,
  WHOLE_APP_CI_JOBS,
  WHOLE_APP_EXTENDED_E2E_SPECS,
  WHOLE_APP_E2E_SPECS,
  WHOLE_APP_PROD_E2E_SPECS,
  WHOLE_APP_UI_RELEASE_TAG,
  WHOLE_APP_UNIT_TEST_FILES,
  wholeAppE2eSpecCount,
  wholeAppExtendedE2eSpecCount,
  wholeAppUnitTestFileCount,
} from "@/lib/hive-release-gate-spec";

describe("hive-release-gate-spec", () => {
  it("lists unique E2E spec files including release gate", () => {
    expect(new Set(WHOLE_APP_E2E_SPECS).size).toBe(WHOLE_APP_E2E_SPECS.length);
    expect(WHOLE_APP_E2E_SPECS).toContain("whole-app-release-gate.spec.ts");
    expect(wholeAppE2eSpecCount()).toBeGreaterThanOrEqual(11);
  });

  it("covers unit tests for IA, shell, settings, and journeys", () => {
    expect(WHOLE_APP_UNIT_TEST_FILES).toContain("lib/hive-ia-canonical.test.ts");
    expect(WHOLE_APP_UNIT_TEST_FILES).toContain("lib/hive-critical-journeys-spec.test.ts");
    expect(WHOLE_APP_UNIT_TEST_FILES.length).toBeGreaterThanOrEqual(10);
  });

  it("defines release gate invariants", () => {
    const ids = HIVE_RELEASE_GATE_INVARIANTS.map((row) => row.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toContain("desktop-no-duplicate-search");
    expect(ids).toContain("zone-shell-present");
    expect(ids).toContain("modal-migration-complete");
    expect(ids).toContain("popover-migration-complete");
  });

  it("unit test bundle matches SSOT count (sync with whole-app-ui-release-gate.sh)", () => {
    expect(wholeAppUnitTestFileCount()).toBe(WHOLE_APP_UNIT_TEST_FILES.length);
    expect(WHOLE_APP_UNIT_TEST_FILES.length).toBe(21);
  });

  it("exports aligned version bundle", () => {
    const bundle = hiveReleaseGateVersionBundle();
    expect(bundle.ia).toMatch(/^2026\.\d+-v\d+$/);
    expect(bundle.pageShell).toMatch(/^2026\.\d+-v\d+$/);
    expect(bundle.journeys).toMatch(/^2026\.\d+-v\d+$/);
    expect(bundle.releaseGate).toMatch(/^2026\.\d+-v\d+$/);
  });

  it("zone specs are covered by shell invariant intent", () => {
    expect(HIVE_PAGE_ZONE_SPECS.length).toBeGreaterThanOrEqual(8);
  });

  it("documents CI jobs and extended visual specs", () => {
    expect(WHOLE_APP_CI_JOBS.coreGate).toBe("whole_app_ui_gate");
    expect(WHOLE_APP_CI_JOBS.extendedGate).toBe("whole_app_ui_extended");
    expect(WHOLE_APP_CI_JOBS.prodJourneys).toBe("whole_app_prod_journeys");
    expect(wholeAppExtendedE2eSpecCount()).toBe(WHOLE_APP_EXTENDED_E2E_SPECS.length);
    expect(WHOLE_APP_EXTENDED_E2E_SPECS).toContain("responsive-visual.spec.ts");
    expect(WHOLE_APP_PROD_E2E_SPECS).toContain("whole-app-prod-journeys.spec.ts");
  });

  it("defines shippable release tag aligned with gate version", () => {
    expect(WHOLE_APP_UI_RELEASE_TAG).toBe("v2026.05-whole-app-ui");
    expect(HIVE_RELEASE_GATE_VERSION).toBe("2026.05-v5");
    expect(hiveReleaseGateVersionBundle().releaseGate).toBe(HIVE_RELEASE_GATE_VERSION);
  });
});
