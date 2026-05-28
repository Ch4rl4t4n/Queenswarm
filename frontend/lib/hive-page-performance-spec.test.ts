/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import {
  hivePerformanceErrorCoverage,
  hivePerformanceLoadingCoverage,
  HIVE_PERFORMANCE_SPECS,
  HIVE_ZONE_PERFORMANCE_SPECS,
} from "@/lib/hive-page-performance-spec";

describe("hive-page-performance-spec", () => {
  it("defines zone and secondary route coverage", () => {
    expect(HIVE_ZONE_PERFORMANCE_SPECS.length).toBeGreaterThanOrEqual(8);
    expect(HIVE_PERFORMANCE_SPECS.length).toBeGreaterThan(HIVE_ZONE_PERFORMANCE_SPECS.length);
  });

  it("every spec route has loading.tsx on disk", () => {
    const rows = hivePerformanceLoadingCoverage();
    const missing = rows.filter((row) => !row.ok);
    expect(missing, `missing loading files: ${missing.map((m) => m.file).join(", ")}`).toEqual([]);
  });

  it("every spec route has error.tsx on disk", () => {
    const rows = hivePerformanceErrorCoverage();
    const missing = rows.filter((row) => !row.ok);
    expect(missing, `missing error files: ${missing.map((m) => m.file).join(", ")}`).toEqual([]);
  });
});
