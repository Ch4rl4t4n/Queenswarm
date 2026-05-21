import { describe, expect, it } from "vitest";

import {
  auditDigestHealthLabel,
  auditDigestHealthTone,
  formatDigestSentAt,
  tenantDigestNeedsManualSend,
  rollupDigestNeedsBulkSend,
} from "@/lib/audit-rollup-utils";

describe("auditDigestHealthLabel", () => {
  it("maps health codes to operator labels", () => {
    expect(auditDigestHealthLabel("healthy")).toBe("On schedule");
    expect(auditDigestHealthLabel("stale")).toBe("Stale delivery");
    expect(auditDigestHealthLabel("never_sent")).toBe("Never sent");
    expect(auditDigestHealthLabel("disabled")).toBe("Digest off");
  });
});

describe("auditDigestHealthTone", () => {
  it("maps stale and never_sent to warn/danger tones", () => {
    expect(auditDigestHealthTone("healthy")).toBe("ok");
    expect(auditDigestHealthTone("stale")).toBe("err");
    expect(auditDigestHealthTone("never_sent")).toBe("warn");
  });
});

describe("rollupDigestNeedsBulkSend", () => {
  it("returns true when stale or never_sent counts exist", () => {
    expect(rollupDigestNeedsBulkSend({ stale: 1 })).toBe(true);
    expect(rollupDigestNeedsBulkSend({ never_sent: 2 })).toBe(true);
    expect(rollupDigestNeedsBulkSend({ healthy: 3 })).toBe(false);
  });
});

describe("tenantDigestNeedsManualSend", () => {
  it("returns true only for stale and never_sent", () => {
    expect(tenantDigestNeedsManualSend("stale")).toBe(true);
    expect(tenantDigestNeedsManualSend("never_sent")).toBe(true);
    expect(tenantDigestNeedsManualSend("healthy")).toBe(false);
    expect(tenantDigestNeedsManualSend("disabled")).toBe(false);
  });
});

describe("formatDigestSentAt", () => {
  it("returns null for empty values", () => {
    expect(formatDigestSentAt(null)).toBeNull();
    expect(formatDigestSentAt("")).toBeNull();
  });

  it("formats valid ISO timestamps", () => {
    expect(formatDigestSentAt("2026-05-19T08:30:00+00:00")).toMatch(/May/);
  });
});
