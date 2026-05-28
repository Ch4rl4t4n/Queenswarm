import { describe, expect, it } from "vitest";

import { pathnameMatchesRoute } from "./use-route-scoped-poll";

describe("pathnameMatchesRoute", () => {
  it("matches overview aliases when active route is root", () => {
    expect(pathnameMatchesRoute("/agentic-os", "/")).toBe(true);
    expect(pathnameMatchesRoute("/cockpit", "/")).toBe(true);
    expect(pathnameMatchesRoute("/dashboard", "/")).toBe(true);
    expect(pathnameMatchesRoute("/overview", "/")).toBe(true);
    expect(pathnameMatchesRoute("/", "/")).toBe(true);
  });

  it("does not match unrelated routes for root scope", () => {
    expect(pathnameMatchesRoute("/agents", "/")).toBe(false);
    expect(pathnameMatchesRoute("/cockpit/extra", "/")).toBe(false);
  });

  it("matches prefixed routes", () => {
    expect(pathnameMatchesRoute("/agents", "/agents")).toBe(true);
    expect(pathnameMatchesRoute("/agents/123", "/agents")).toBe(true);
    expect(pathnameMatchesRoute("/cockpit", "/agents")).toBe(false);
  });
});
