"use client";

import { useDashboardSection, useDashboardSettings } from "@/components/hive/dashboard-layout-provider";
import type { DashboardSectionId } from "@/lib/dashboard-layout-preferences";

const TELEMETRY_SECTIONS: DashboardSectionId[] = [
  "agents",
  "kpiStats",
  "pollenCosts",
  "taskQueue",
  "recentTasks",
  "queenMission",
  "performanceTier",
  "ballroomParticipants",
];

const SUMMARY_SECTIONS: DashboardSectionId[] = ["kpiStats", "pollenCosts", "agents", "performanceTier"];

function anySectionVisible(ids: DashboardSectionId[], isVisible: (id: DashboardSectionId) => boolean): boolean {
  return ids.some((id) => isVisible(id));
}

/**
 * Gate high-frequency dashboard telemetry polls when operator hides all live sections
 * or opens the layout settings flyout (canvas paused).
 */
export function useDashboardTelemetryPollEnabled(): boolean {
  const { settingsOpen } = useDashboardSettings();
  const showAgents = useDashboardSection("agents");
  const showKpi = useDashboardSection("kpiStats");
  const showPollenCosts = useDashboardSection("pollenCosts");
  const showTaskQueue = useDashboardSection("taskQueue");
  const showRecentTasks = useDashboardSection("recentTasks");
  const showQueenMission = useDashboardSection("queenMission");
  const showPerformanceTier = useDashboardSection("performanceTier");
  const showBallroom = useDashboardSection("ballroomParticipants");

  if (settingsOpen) {
    return false;
  }

  return (
    showAgents ||
    showKpi ||
    showPollenCosts ||
    showTaskQueue ||
    showRecentTasks ||
    showQueenMission ||
    showPerformanceTier ||
    showBallroom
  );
}

/** Slower summary/cost polls — KPI tiles and cost window only. */
export function useDashboardSummaryPollEnabled(): boolean {
  const { settingsOpen } = useDashboardSettings();
  const showKpi = useDashboardSection("kpiStats");
  const showPollenCosts = useDashboardSection("pollenCosts");
  const showAgents = useDashboardSection("agents");
  const showPerformanceTier = useDashboardSection("performanceTier");

  if (settingsOpen) {
    return false;
  }

  return showKpi || showPollenCosts || showAgents || showPerformanceTier;
}

/** Test helper — evaluate visibility from a layout map. */
export function dashboardTelemetryPollEnabledFromLayout(
  layout: Record<DashboardSectionId, boolean>,
  settingsOpen: boolean,
): boolean {
  if (settingsOpen) {
    return false;
  }
  return anySectionVisible(TELEMETRY_SECTIONS, (id) => layout[id]);
}

export function dashboardSummaryPollEnabledFromLayout(
  layout: Record<DashboardSectionId, boolean>,
  settingsOpen: boolean,
): boolean {
  if (settingsOpen) {
    return false;
  }
  return anySectionVisible(SUMMARY_SECTIONS, (id) => layout[id]);
}
