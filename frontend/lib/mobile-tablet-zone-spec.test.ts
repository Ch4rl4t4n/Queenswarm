import { describe, expect, it } from "vitest";

import {
  MOBILE_TABLET_SECONDARY_ROUTE_SPECS,
  MOBILE_TABLET_ZONE_ROUTE_SPECS,
  mobileTabletRouteSpecCount,
} from "@/lib/mobile-tablet-zone-spec";
import { mobileChromeTitleForPath } from "@/lib/mobile-tablet-chrome";

describe("mobile-tablet-zone-spec", () => {
  it("includes zone and secondary route matrices", () => {
    expect(MOBILE_TABLET_ZONE_ROUTE_SPECS.length).toBeGreaterThanOrEqual(8);
    expect(MOBILE_TABLET_SECONDARY_ROUTE_SPECS.length).toBeGreaterThanOrEqual(18);
    expect(mobileTabletRouteSpecCount()).toBe(
      MOBILE_TABLET_ZONE_ROUTE_SPECS.length + MOBILE_TABLET_SECONDARY_ROUTE_SPECS.length,
    );
  });

  it("secondary routes resolve mobile chrome titles", () => {
    for (const spec of MOBILE_TABLET_SECONDARY_ROUTE_SPECS) {
      const chrome = mobileChromeTitleForPath(spec.path);
      expect(chrome.title).toBe(spec.mobileTitle);
    }
  });
});
