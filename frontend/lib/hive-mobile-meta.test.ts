import { describe, expect, it } from "vitest";

import { hiveMobileRouteMeta } from "./hive-mobile-meta";

describe("hiveMobileRouteMeta", () => {
  it("returns dashboard meta for root", () => {
    const m = hiveMobileRouteMeta("/");
    expect(m.kicker).toBe("Dashboard");
  });

  it("returns ballroom meta with pageTitleSuffix", () => {
    const m = hiveMobileRouteMeta("/ballroom");
    expect(m.kicker).toBe("Ballroom");
    expect(m.pageTitleSuffix).toBe("Ballroom");
  });

  it("treats settings subtree as Settings", () => {
    expect(hiveMobileRouteMeta("/settings/security").kicker).toBe("Settings");
  });

  it("fallbacks to QueenSwarm for unknown routes", () => {
    expect(hiveMobileRouteMeta("/unknown/route").kicker).toBe("QueenSwarm");
  });
});
