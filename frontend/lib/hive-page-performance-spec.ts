/**
 * Whole-App UI Reorder — Phase 8 route performance coverage (loading + error segments).
 */

import { existsSync } from "node:fs";
import { join } from "node:path";

import { HIVE_PAGE_ZONE_SPECS } from "@/lib/hive-page-zone-spec";

export interface HiveRoutePerformanceSpec {
  path: string;
  title: string;
  /** Path under `frontend/` to `loading.tsx`. */
  loadingFile: string;
  /** Path under `frontend/` to `error.tsx` when required. */
  errorFile: string;
  withSubnav?: boolean;
}

const FRONTEND_ROOT = join(process.cwd());

function dashboardSegment(routePath: string): string {
  const segment = routePath.replace(/^\//, "");
  return join("app", "(dashboard)", segment, "loading.tsx");
}

function dashboardErrorSegment(routePath: string): string {
  const segment = routePath.replace(/^\//, "");
  return join("app", "(dashboard)", segment, "error.tsx");
}

/** IA zone routes — must expose HivePageShell-aligned loading + error boundaries. */
export const HIVE_ZONE_PERFORMANCE_SPECS: HiveRoutePerformanceSpec[] = HIVE_PAGE_ZONE_SPECS.map((spec) => ({
  path: spec.path,
  title: spec.title,
  loadingFile: dashboardSegment(spec.path),
  errorFile: dashboardErrorSegment(spec.path),
  withSubnav: spec.hasSubnav,
}));

/** High-traffic secondary routes included in Phase 8 pass. */
export const HIVE_SECONDARY_PERFORMANCE_SPECS: HiveRoutePerformanceSpec[] = [
  {
    path: "/settings/security",
    title: "Settings",
    loadingFile: join("app", "(dashboard)", "settings", "loading.tsx"),
    errorFile: join("app", "(dashboard)", "settings", "error.tsx"),
    withSubnav: true,
  },
  {
    path: "/manual",
    title: "Manual",
    loadingFile: join("app", "(dashboard)", "manual", "loading.tsx"),
    errorFile: join("app", "(dashboard)", "manual", "error.tsx"),
  },
  {
    path: "/foragers",
    title: "Foragers",
    loadingFile: join("app", "(dashboard)", "foragers", "loading.tsx"),
    errorFile: join("app", "(dashboard)", "foragers", "error.tsx"),
  },
  {
    path: "/factory",
    title: "Micro-SaaS Factory",
    loadingFile: join("app", "(dashboard)", "factory", "loading.tsx"),
    errorFile: join("app", "(dashboard)", "factory", "error.tsx"),
  },
  {
    path: "/workflows",
    title: "Workflows",
    loadingFile: join("app", "(dashboard)", "workflows", "loading.tsx"),
    errorFile: join("app", "(dashboard)", "workflows", "error.tsx"),
  },
  {
    path: "/jobs",
    title: "Async workflow jobs",
    loadingFile: join("app", "(dashboard)", "(features)", "jobs", "loading.tsx"),
    errorFile: join("app", "(dashboard)", "(features)", "jobs", "error.tsx"),
  },
];

export const HIVE_PERFORMANCE_SPECS: HiveRoutePerformanceSpec[] = [
  ...HIVE_ZONE_PERFORMANCE_SPECS,
  ...HIVE_SECONDARY_PERFORMANCE_SPECS,
];

/** Verify loading.tsx exists for every spec entry. */
export function hivePerformanceLoadingCoverage(): { path: string; ok: boolean; file: string }[] {
  return HIVE_PERFORMANCE_SPECS.map((spec) => ({
    path: spec.path,
    file: spec.loadingFile,
    ok: existsSync(join(FRONTEND_ROOT, spec.loadingFile)),
  }));
}

/** Verify error.tsx exists for every spec entry. */
export function hivePerformanceErrorCoverage(): { path: string; ok: boolean; file: string }[] {
  return HIVE_PERFORMANCE_SPECS.map((spec) => ({
    path: spec.path,
    file: spec.errorFile,
    ok: existsSync(join(FRONTEND_ROOT, spec.errorFile)),
  }));
}
