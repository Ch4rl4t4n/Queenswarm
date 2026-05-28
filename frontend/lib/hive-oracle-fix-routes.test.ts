import { describe, expect, it } from "vitest";

import { executionStudioSectionHref, executionStudioWorkspaceFromHash } from "@/lib/integrations-routes";
import { normalizeOracleFixHref, oracleFixLabel } from "@/lib/hive-oracle-fix-routes";

describe("executionStudioWorkspaceFromHash", () => {
  it("maps publish lane anchors to publish workspace", () => {
    expect(executionStudioWorkspaceFromHash("#publish-queue")).toBe("publish");
    expect(executionStudioWorkspaceFromHash("#trading-cockpit")).toBe("publish");
  });

  it("maps innovation lab anchor", () => {
    expect(executionStudioWorkspaceFromHash("#innovation-lab")).toBe("innovation");
  });
});

describe("executionStudioSectionHref", () => {
  it("includes section query and scroll hash", () => {
    expect(executionStudioSectionHref("publish", "publish-queue")).toBe(
      "/integrations?tab=studio&section=publish#publish-queue",
    );
  });
});

describe("hive-oracle-fix-routes", () => {
  it("labels publish backlog CTA", () => {
    expect(oracleFixLabel("publish_backlog")).toBe("Review queue");
  });

  it("upgrades legacy studio publish links", () => {
    expect(normalizeOracleFixHref("/integrations?tab=studio#publish-queue")).toBe(
      "/integrations?tab=studio&section=publish#publish-queue",
    );
  });
});
