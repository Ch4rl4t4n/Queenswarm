import { describe, expect, it } from "vitest";

import {
  agentsEcosystemSectionFromHash,
  agentsEcosystemSectionHref,
} from "@/lib/agents-ecosystem-routes";

describe("agentsEcosystemSectionFromHash", () => {
  it("maps legacy supervisor and hierarchy hashes", () => {
    expect(agentsEcosystemSectionFromHash("#sessions")).toBe("sessions");
    expect(agentsEcosystemSectionFromHash("#hierarchy")).toBe("hierarchy");
    expect(agentsEcosystemSectionFromHash("#context-graph")).toBe("context");
  });

  it("returns null for unknown hash", () => {
    expect(agentsEcosystemSectionFromHash("#unknown")).toBeNull();
  });

  it("maps deep-link anchors to the tab that mounts them", () => {
    expect(agentsEcosystemSectionFromHash("#first-run-wizard")).toBe("sessions");
    expect(agentsEcosystemSectionFromHash("#agent-suggestions")).toBe("learning");
  });
});

describe("agentsEcosystemSectionHref", () => {
  it("preserves canonical paths for default and legacy links", () => {
    expect(agentsEcosystemSectionHref("roles")).toBe("/agents#roles");
    expect(agentsEcosystemSectionHref("sessions")).toBe("/agents#sessions");
    expect(agentsEcosystemSectionHref("context")).toBe("/agents#context-graph");
  });
});
