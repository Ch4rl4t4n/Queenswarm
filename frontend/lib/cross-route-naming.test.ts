import { describe, expect, it } from "vitest";

import {
  AGENTIC_OS_CANONICAL_PATH,
  AGENTIC_OS_PRODUCT_NAME,
  isAgenticOsRoute,
} from "@/lib/cross-route-naming";
import { hiveOverviewHref, hiveOverviewLabel, soloOperatorHomePreferred } from "@/lib/hive-home-route";
import { hiveMobileRouteMeta } from "@/lib/hive-mobile-meta";
import { cockpitSectionHref } from "@/lib/cockpit-routes";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";

describe("cross-route-naming", () => {
  it("uses overview href and label from hive-home-route when CP enabled", () => {
    if (!OPERATOR_CONTROL_PLANE_ENABLED) {
      return;
    }
    if (soloOperatorHomePreferred()) {
      expect(hiveOverviewHref()).toBe("/tasks");
      expect(hiveOverviewLabel()).toBe("Mission Control");
    } else {
      expect(hiveOverviewHref()).toBe(AGENTIC_OS_CANONICAL_PATH);
      expect(hiveOverviewLabel()).toBe(AGENTIC_OS_PRODUCT_NAME);
    }
  });

  it("mobile meta shows Agentic OS on canonical and legacy paths", () => {
    if (!OPERATOR_CONTROL_PLANE_ENABLED) {
      return;
    }
    for (const path of ["/", "/agentic-os", "/cockpit"]) {
      const meta = hiveMobileRouteMeta(path);
      expect(meta.kicker).toBe(AGENTIC_OS_PRODUCT_NAME);
      expect(meta.pageTitleSuffix).toBe(AGENTIC_OS_PRODUCT_NAME);
    }
  });

  it("cockpit section hrefs use canonical agentic-os path", () => {
    expect(cockpitSectionHref("icm")).toBe("/agentic-os#icm");
  });

  it("recognizes agentic os route aliases", () => {
    expect(isAgenticOsRoute("/agentic-os")).toBe(true);
    expect(isAgenticOsRoute("/cockpit")).toBe(true);
    expect(isAgenticOsRoute("/agents")).toBe(false);
  });
});
