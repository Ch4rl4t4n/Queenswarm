import { describe, expect, it } from "vitest";

import { hubEcosystemLanes } from "@/lib/hub-ecosystem-lanes";

describe("hubEcosystemLanes", () => {
  it("ballroom preset links integrations supervisor hivemind", () => {
    const labels = hubEcosystemLanes("ballroom").map((lane) => lane.label);
    expect(labels).toEqual(["Integrations", "Supervisor", "HiveMind"]);
    expect(hubEcosystemLanes("ballroom")[0]?.href).toBe("/integrations?tab=active#ecosystem");
  });

  it("agents preset includes tasks and ballroom", () => {
    const labels = hubEcosystemLanes("agents").map((lane) => lane.label);
    expect(labels).toContain("Tasks");
    expect(labels).toContain("Ballroom");
  });

  it("tasks preset includes supervisor and integrations ecosystem anchor", () => {
    const lanes = hubEcosystemLanes("tasks");
    expect(lanes[0]?.href).toBe("/integrations?tab=active#ecosystem");
    expect(lanes.map((lane) => lane.label)).toContain("Supervisor");
  });

  it("dashboard preset links agents tasks integrations ballroom", () => {
    const labels = hubEcosystemLanes("dashboard").map((lane) => lane.label);
    expect(labels).toEqual(["Agents", "Tasks", "Integrations", "Ballroom"]);
  });

  it("integrations preset links supervisor tasks hivemind ballroom", () => {
    const labels = hubEcosystemLanes("integrations").map((lane) => lane.label);
    expect(labels).toContain("Supervisor");
    expect(labels).toContain("HiveMind");
  });
});
