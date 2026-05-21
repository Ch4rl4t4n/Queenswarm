import { describe, expect, it } from "vitest";

import { goalSearchQuery, matchGraphNodeFocusIds, probeGoalTokens } from "./hive-graph-focus";

describe("hive-graph-focus", () => {
  it("extracts goal tokens", () => {
    expect(probeGoalTokens("Research competitor pricing for SaaS onboarding")).toEqual([
      "research",
      "competitor",
      "pricing",
      "saas",
      "onboarding",
    ]);
  });

  it("matches nodes from goal tokens and semantic hits", () => {
    const nodes = [
      { id: "n1", label: "Pricing playbook" },
      { id: "n2", label: "Unrelated" },
    ];
    const hits = [{ document: "SaaS onboarding checklist", metadata: { title: "Onboarding" } }];
    const focused = matchGraphNodeFocusIds(nodes, hits, ["pricing", "saas"]);
    expect(focused.has("n1")).toBe(true);
    expect(focused.has("n2")).toBe(false);
  });

  it("clips long goal search queries", () => {
    const long = "word ".repeat(80).trim();
    expect(goalSearchQuery(long, 40).length).toBeLessThanOrEqual(40);
  });
});
