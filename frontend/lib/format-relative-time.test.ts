import { describe, expect, it } from "vitest";

import {
  formatDurationSeconds,
  formatHoursLikeCommandCenter,
  formatTimeAgoSeconds,
} from "@/lib/format-relative-time";

describe("formatDurationSeconds", () => {
  it("when_under_one_minute_then_shows_seconds", () => {
    expect(formatDurationSeconds(45)).toBe("45s");
  });

  it("when_under_one_hour_then_shows_minutes", () => {
    expect(formatDurationSeconds(125)).toBe("2m");
  });

  it("when_under_one_day_then_shows_hours", () => {
    expect(formatDurationSeconds(3700)).toBe("1.0h");
    expect(formatDurationSeconds(36_000)).toBe("10h");
  });

  it("when_over_one_day_then_shows_decimal_days", () => {
    expect(formatDurationSeconds(610_985)).toBe("7.1d");
  });

  it("when_verbose_under_one_hour_then_shows_minutes_and_seconds", () => {
    expect(formatDurationSeconds(125, { style: "verbose" })).toBe("2m 5s");
  });

  it("when_ago_suffix_then_appends_ago", () => {
    expect(formatDurationSeconds(3600, { suffix: "ago" })).toBe("1h ago");
  });
});

describe("formatTimeAgoSeconds", () => {
  it("when_null_then_returns_null_label", () => {
    expect(formatTimeAgoSeconds(null, { nullLabel: "awaiting" })).toBe("awaiting");
  });
});

describe("formatHoursLikeCommandCenter", () => {
  it("when_over_24h_then_shows_days", () => {
    expect(formatHoursLikeCommandCenter(79.2)).toBe("3.3d");
  });

  it("when_under_24h_then_shows_hours", () => {
    expect(formatHoursLikeCommandCenter(12)).toBe("12h");
  });
});
