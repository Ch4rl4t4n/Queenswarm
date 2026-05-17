import { describe, expect, it } from "vitest";

import {
  extractPhase3FromCatalog,
  orderedPhase3Categories,
  phase3ProvisionCoverage,
  type Phase3TemplatePublic,
} from "./connectors-phase3";

describe("connectors-phase3 helpers", () => {
  it("extractPhase3FromCatalog returns null when phase3 missing", () => {
    expect(extractPhase3FromCatalog({})).toBeNull();
    expect(extractPhase3FromCatalog(null)).toBeNull();
  });

  it("extractPhase3FromCatalog parses grouped templates", () => {
    const tpl: Phase3TemplatePublic = {
      template_id: "gmail_google_workspace",
      category: "email",
      title: "Gmail",
      summary: "Test summary for gmail connector template.",
      documentation_url: "https://developers.google.com/gmail/api/reference/rest",
      suggested_slug: "gmail_workspace",
      auth_type: "oauth2",
      base_url: "https://gmail.googleapis.com",
      suggested_manager_slugs: [],
      tools: [],
      tool_count: 0,
    };
    const slice = extractPhase3FromCatalog({
      phase3: {
        template_count: 1,
        template_ids: ["gmail_google_workspace"],
        templates: [tpl],
        grouped: { email: [tpl] },
      },
    });
    expect(slice?.templates).toHaveLength(1);
    expect(slice?.grouped.email).toHaveLength(1);
  });

  it("orderedPhase3Categories prefers hive ordering then tails", () => {
    const grouped: Record<string, Phase3TemplatePublic[]> = {
      billing: [],
      email: [],
      zebra: [],
    };
    expect(orderedPhase3Categories(grouped)).toEqual(["email", "billing", "zebra"]);
  });

  it("phase3ProvisionCoverage matches suggested slugs case-insensitively", () => {
    const tpl: Phase3TemplatePublic = {
      template_id: "x",
      category: "chat",
      title: "X",
      summary: "Summary text long enough for schema validation in UI typings only.",
      documentation_url: "https://example.com/docs",
      suggested_slug: "Alpha_SLUG",
      auth_type: "none",
      base_url: null,
      suggested_manager_slugs: [],
      tools: [],
      tool_count: 0,
    };
    const rows = phase3ProvisionCoverage([tpl], ["alpha_slug"]);
    expect(rows[0]?.provisioned).toBe(true);
  });
});
