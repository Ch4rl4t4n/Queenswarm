import { describe, expect, it } from "vitest";

import { filterSectionNavItems, sectionDensityClass } from "./section-hub";

const ITEMS = [
  { href: "/tasks", title: "Tasks", description: "Backlog lifecycle and status." },
  { href: "/workflows", title: "Workflows", description: "Visual DAG controls." },
  { href: "/monitoring", title: "Monitoring", description: "Host pressure and telemetry diagnostics." },
];

describe("section-hub", () => {
  it("returns full item set when query is empty", () => {
    expect(filterSectionNavItems(ITEMS, "")).toEqual(ITEMS);
    expect(filterSectionNavItems(ITEMS, "   ")).toEqual(ITEMS);
  });

  it("filters by title and description with case-insensitive matching", () => {
    expect(filterSectionNavItems(ITEMS, "flow")).toEqual([ITEMS[1]]);
    expect(filterSectionNavItems(ITEMS, "TELEMETRY")).toEqual([ITEMS[2]]);
  });

  it("maps compact density class for cards", () => {
    expect(sectionDensityClass("compact")).toContain("p-3");
    expect(sectionDensityClass("comfortable")).toContain("p-4");
  });
});
