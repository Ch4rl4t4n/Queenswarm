import { describe, expect, it } from "vitest";

import { buildUserStatusBadges } from "@/lib/user-status-badges";

describe("buildUserStatusBadges", () => {
  it("returns_only_tier_for_commercial_free_user_with_2fa", () => {
    const badges = buildUserStatusBadges({
      language: "en",
      subscriptionTier: "free",
      platformMode: "commercial",
      isAdmin: false,
      totpEnabled: true,
    });
    expect(badges.map((b) => b.label)).toEqual(["Regular"]);
  });

  it("returns_no_badges_for_internal_admin_operator", () => {
    const badges = buildUserStatusBadges({
      language: "en",
      subscriptionTier: "pro",
      platformMode: "internal",
      isAdmin: true,
      totpEnabled: false,
    });
    expect(badges.map((b) => b.label)).toEqual([]);
  });
});
