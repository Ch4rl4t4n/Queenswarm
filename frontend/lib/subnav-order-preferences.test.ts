import { beforeEach, describe, expect, it } from "vitest";

import { resolveIntegrationsTab } from "@/lib/integrations-routes";
import {
  filterEnabledSubnavIds,
  primarySubnavDefaultId,
  saveSubnavOrder,
  saveSubnavDisabledIds,
  SUBNAV_MENU_KEYS,
  subnavOrderStorageKey,
  subnavDisabledStorageKey,
} from "@/lib/subnav-order-preferences";

function installBrowserMocks(): void {
  const store = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { localStorage },
  });
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: localStorage,
  });
}

describe("primarySubnavDefaultId", () => {
  beforeEach(() => {
    installBrowserMocks();
  });

  it("returns first visible id when no saved order", () => {
    expect(primarySubnavDefaultId(SUBNAV_MENU_KEYS.integrationsPrimary, ["hub", "active"], "active")).toBe(
      "hub",
    );
  });

  it("returns first id from saved order", () => {
    saveSubnavOrder(SUBNAV_MENU_KEYS.integrationsPrimary, ["marketplace", "hub", "active"]);
    expect(
      primarySubnavDefaultId(
        SUBNAV_MENU_KEYS.integrationsPrimary,
        ["hub", "active", "marketplace"],
        "active",
      ),
    ).toBe("marketplace");
  });
});

describe("resolveIntegrationsTab with saved order", () => {
  beforeEach(() => {
    installBrowserMocks();
  });

  it("uses saved first tab when URL is bare", () => {
    saveSubnavOrder(SUBNAV_MENU_KEYS.integrationsPrimary, ["hub", "active", "studio"]);
    expect(resolveIntegrationsTab({})).toBe("hub");
  });

  it("still prefers explicit query tab", () => {
    saveSubnavOrder(SUBNAV_MENU_KEYS.integrationsPrimary, ["hub", "active"]);
    expect(resolveIntegrationsTab({ queryTab: "active" })).toBe("active");
  });

  it("persists under expected storage key", () => {
    saveSubnavOrder(SUBNAV_MENU_KEYS.integrationsPrimary, ["hub", "active"]);
    expect(window.localStorage.getItem(subnavOrderStorageKey(SUBNAV_MENU_KEYS.integrationsPrimary))).toBe(
      JSON.stringify(["hub", "active"]),
    );
  });
});

describe("filterEnabledSubnavIds", () => {
  beforeEach(() => {
    installBrowserMocks();
  });

  it("excludes disabled sections", () => {
    saveSubnavDisabledIds(SUBNAV_MENU_KEYS.integrationsPrimary, new Set(["active", "studio"]));
    expect(filterEnabledSubnavIds(SUBNAV_MENU_KEYS.integrationsPrimary, ["hub", "active", "studio"])).toEqual([
      "hub",
    ]);
  });

  it("keeps at least one section when all are disabled", () => {
    saveSubnavDisabledIds(
      SUBNAV_MENU_KEYS.integrationsPrimary,
      new Set(["hub", "active", "studio"]),
    );
    expect(filterEnabledSubnavIds(SUBNAV_MENU_KEYS.integrationsPrimary, ["hub", "active", "studio"])).toEqual([
      "hub",
      "active",
      "studio",
    ]);
  });

  it("persists disabled ids under expected storage key", () => {
    saveSubnavDisabledIds(SUBNAV_MENU_KEYS.integrationsPrimary, new Set(["active"]));
    expect(window.localStorage.getItem(subnavDisabledStorageKey(SUBNAV_MENU_KEYS.integrationsPrimary))).toBe(
      JSON.stringify(["active"]),
    );
  });
});
