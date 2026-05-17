import { describe, expect, it } from "vitest";

import {
  parsePhase3IntegrationOverview,
  phase3OverviewCoverageScore,
} from "./connectors-phase3-overview";

describe("parsePhase3IntegrationOverview", () => {
  it("returns_null_when_templates_missing", () => {
    expect(parsePhase3IntegrationOverview({ generated_at: "x" })).toBeNull();
  });

  it("parses_valid_overview_envelope", () => {
    const raw = {
      generated_at: "2026-05-14T00:00:00Z",
      dashboard_user_id: "u1",
      templates: [
        {
          template_id: "gmail_google_workspace",
          category: "email",
          title: "Gmail",
          summary: "s",
          suggested_slug: "gmail_workspace",
          documentation_url: "https://example.com",
          auth_type: "oauth2",
          tool_count: 3,
          suggested_manager_slugs: [],
          hub_row: null,
        },
      ],
      obsidian: {
        watch_enabled: false,
        poll_interval_sec: 120,
        max_files_per_sync: 50,
        snapshot: {},
      },
      cross_links: {},
    };
    const parsed = parsePhase3IntegrationOverview(raw);
    expect(parsed?.templates).toHaveLength(1);
    expect(parsed?.templates[0]?.template_id).toBe("gmail_google_workspace");
  });
});

describe("phase3OverviewCoverageScore", () => {
  it("counts_provisioned_and_active_hub_rows", () => {
    const score = phase3OverviewCoverageScore([
      {
        template_id: "a",
        category: "email",
        title: "A",
        summary: "x",
        suggested_slug: "a",
        documentation_url: "https://x",
        auth_type: "oauth2",
        tool_count: 1,
        suggested_manager_slugs: [],
        hub_row: {
          id: "1",
          slug: "a",
          display_name: "A",
          base_url: "https://x",
          auth_type: "oauth2",
          mcp_manifest: null,
          allowed_manager_slugs: [],
          is_active: true,
          is_builtin: false,
          builtin_kind: null,
          last_tested_at: null,
        },
      },
      {
        template_id: "b",
        category: "chat",
        title: "B",
        summary: "y",
        suggested_slug: "b",
        documentation_url: "https://y",
        auth_type: "bearer_token",
        tool_count: 1,
        suggested_manager_slugs: [],
        hub_row: null,
      },
    ]);
    expect(score).toEqual({ provisioned: 1, active: 1, total: 2 });
  });
});
