import { describe, expect, it } from "vitest";

import {
  filterNavByFeatures,
  isRouteAllowed,
  resolvePlatformFeaturesFallback,
  routeFeatureKey,
} from "./platform-features";

describe("platform-features", () => {
  it("internal admin enables factory features", () => {
    const features = resolvePlatformFeaturesFallback({
      platformMode: "internal",
      isAdmin: true,
      subscriptionTier: "free",
    });
    expect(features.skills_export_factory).toBe(true);
    expect(features.foragers).toBe(true);
    expect(features.bee_gamification).toBe(true);
    expect(features.enterprise_workspace).toBe(true);
  });

  it("commercial pro hides factory", () => {
    const features = resolvePlatformFeaturesFallback({
      platformMode: "commercial",
      isAdmin: false,
      subscriptionTier: "pro",
    });
    expect(features.skills_export_factory).toBe(false);
    expect(features.skills_marketplace).toBe(true);
  });

  it("filters nav items by feature map", () => {
    const features = resolvePlatformFeaturesFallback({
      platformMode: "internal",
      isAdmin: true,
      subscriptionTier: "pro",
    });
    const items = filterNavByFeatures(
      [
        { href: "/foragers", featureKey: "foragers" },
        { href: "/agents", featureKey: "agents" },
      ],
      features,
    );
    expect(items.map((i) => i.href)).toEqual(["/foragers", "/agents"]);
  });

  it("commercial free blocks ballroom and recipes", () => {
    const features = resolvePlatformFeaturesFallback({
      platformMode: "commercial",
      isAdmin: false,
      subscriptionTier: "free",
    });
    expect(features.ballroom).toBe(false);
    expect(features.recipes).toBe(false);
    expect(features.agents).toBe(true);
  });

  it("guards routes", () => {
    const features = resolvePlatformFeaturesFallback({
      platformMode: "internal",
      isAdmin: true,
      subscriptionTier: "pro",
    });
    expect(routeFeatureKey("/settings/security")).toBe("settings");
    expect(isRouteAllowed("/foragers", features)).toBe(true);
    expect(isRouteAllowed("/ballroom", features)).toBe(true);
  });
});
