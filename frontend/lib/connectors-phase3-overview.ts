/** Types + helpers for ``GET /connectors/phase3/integration-overview``. */

import type { DynamicConnectorPayload } from "./connectors-types";

export interface Phase3IntegrationOverviewPayload {
  generated_at: string;
  dashboard_user_id: string;
  templates: Phase3OverviewTemplateRow[];
  obsidian: {
    watch_enabled: boolean;
    poll_interval_sec: number;
    max_files_per_sync: number;
    snapshot: Record<string, unknown>;
  };
  cross_links: Record<string, string>;
  cost_governor_note?: string;
}

export interface Phase3OverviewTemplateRow {
  template_id: string;
  category: string;
  title: string;
  summary: string;
  suggested_slug: string;
  documentation_url: string;
  auth_type: string;
  tool_count: number;
  suggested_manager_slugs: string[];
  hub_row: DynamicConnectorPayload | null;
}

/** Narrow unknown JSON into the overview envelope — returns null when malformed. */
export function parsePhase3IntegrationOverview(body: unknown): Phase3IntegrationOverviewPayload | null {
  if (typeof body !== "object" || body === null) {
    return null;
  }
  const root = body as Partial<Phase3IntegrationOverviewPayload>;
  if (!Array.isArray(root.templates) || typeof root.generated_at !== "string") {
    return null;
  }
  const obs = root.obsidian;
  if (
    typeof obs !== "object" ||
    obs === null ||
    typeof (obs as { watch_enabled?: unknown }).watch_enabled !== "boolean" ||
    typeof (obs as { poll_interval_sec?: unknown }).poll_interval_sec !== "number"
  ) {
    return null;
  }
  return root as Phase3IntegrationOverviewPayload;
}

/** Coverage scored from hub rows that passed provisioning + activation checks. */
export function phase3OverviewCoverageScore(templates: Phase3OverviewTemplateRow[]): {
  provisioned: number;
  active: number;
  total: number;
} {
  let provisioned = 0;
  let active = 0;
  for (const row of templates) {
    if (row.hub_row) {
      provisioned += 1;
      if (row.hub_row.is_active) {
        active += 1;
      }
    }
  }
  return { provisioned, active, total: templates.length };
}
