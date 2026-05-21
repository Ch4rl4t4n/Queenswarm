import { describe, expect, it } from "vitest";

import { formatHiveNotificationBadge } from "@/lib/hooks/use-hive-notification-badge";

describe("formatHiveNotificationBadge", () => {
  it("returns_null_when_zero_or_negative", () => {
    expect(formatHiveNotificationBadge(0)).toBeNull();
    expect(formatHiveNotificationBadge(-1)).toBeNull();
  });

  it("caps_display_at_9_plus", () => {
    expect(formatHiveNotificationBadge(9)).toBe("9");
    expect(formatHiveNotificationBadge(10)).toBe("9+");
    expect(formatHiveNotificationBadge(42)).toBe("9+");
  });
});
