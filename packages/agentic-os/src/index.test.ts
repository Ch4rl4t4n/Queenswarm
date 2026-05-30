import { describe, expect, it } from "vitest";

import { isCommerceOrderSyncEvent, previewSocialPublishGate } from "./index.js";

describe("previewSocialPublishGate", () => {
  it("blocks live when simulate not confirmed", () => {
    const d = previewSocialPublishGate({
      mode: "live",
      liveEnabled: true,
      effectiveConfirmed: false,
      confirmReason: "pack_not_simulated",
    });
    expect(d.allowed).toBe(false);
    expect(d.error_code).toBe("pack_not_simulated");
  });
});

describe("isCommerceOrderSyncEvent", () => {
  it("recognizes commerce_order_sync payloads", () => {
    expect(
      isCommerceOrderSyncEvent({
        event: "commerce_order_sync",
        event_id: "evt_1",
        provider: "stripe",
      }),
    ).toBe(true);
  });
});
