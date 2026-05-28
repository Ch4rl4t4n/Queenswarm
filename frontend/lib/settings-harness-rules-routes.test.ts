import { describe, expect, it } from "vitest";

import {
  harnessRulesSectionFromHash,
  harnessRulesSectionHref,
  resolveHarnessRulesSection,
} from "@/lib/settings-harness-rules-routes";

describe("harnessRulesSectionHref", () => {
  it("returns hash paths for rules sub-sections", () => {
    expect(harnessRulesSectionHref("overview")).toBe("/settings/harness#rules");
    expect(harnessRulesSectionHref("monitoring")).toBe("/settings/harness#rules-monitoring");
    expect(harnessRulesSectionHref("loops")).toBe("/settings/harness#rules-loops");
  });
});

describe("harnessRulesSectionFromHash", () => {
  it("maps rules hash prefix", () => {
    expect(harnessRulesSectionFromHash("#rules")).toBe("overview");
    expect(harnessRulesSectionFromHash("#rules-tools")).toBe("tools");
  });

  it("returns null for unrelated hashes", () => {
    expect(harnessRulesSectionFromHash("#patterns")).toBeNull();
    expect(harnessRulesSectionFromHash("#operator")).toBeNull();
  });
});

describe("resolveHarnessRulesSection", () => {
  it("defaults to overview", () => {
    expect(resolveHarnessRulesSection({})).toBe("overview");
  });

  it("reads hash", () => {
    expect(resolveHarnessRulesSection({ hash: "#rules-skills" })).toBe("skills");
  });
});
