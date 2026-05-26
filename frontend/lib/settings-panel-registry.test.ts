import { describe, expect, it } from "vitest";

import {
  DEFAULT_SETTINGS_PANEL,
  isSettingsNavSectionActive,
  parseSettingsPanelSlug,
  SETTINGS_PANEL_SLUGS,
} from "./settings-panel-registry";

describe("settings-panel-registry", () => {
  it("parses known settings slugs from pathname", () => {
    expect(parseSettingsPanelSlug("/settings/harness")).toBe("harness");
    expect(parseSettingsPanelSlug("/settings/billing/extra")).toBe("billing");
  });

  it("returns null for unknown or non-settings paths", () => {
    expect(parseSettingsPanelSlug("/settings/unknown-panel")).toBeNull();
    expect(parseSettingsPanelSlug("/agents")).toBeNull();
  });

  it("covers every slug with a default fallback", () => {
    expect(SETTINGS_PANEL_SLUGS).toContain(DEFAULT_SETTINGS_PANEL);
  });

  it("matches catch-all panels and dedicated routes like costs", () => {
    expect(isSettingsNavSectionActive("/settings/harness", "/settings/harness")).toBe(true);
    expect(isSettingsNavSectionActive("/settings/costs", "/settings/costs")).toBe(true);
    expect(isSettingsNavSectionActive("/settings/billing", "/settings/security")).toBe(false);
  });
});
