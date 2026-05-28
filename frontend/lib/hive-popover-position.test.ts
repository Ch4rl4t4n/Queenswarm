/**
 * @vitest-environment happy-dom
 */
import { describe, expect, it } from "vitest";

import { computePopoverPosition, popoverPanelWidthPx } from "@/lib/hive-popover-position";

describe("hive-popover-position", () => {
  it("prefers width capped at 85% viewport", () => {
    expect(popoverPanelWidthPx(400, 320)).toBe(320);
    expect(popoverPanelWidthPx(200, 320)).toBe(170);
  });

  it("places panel below anchor by default", () => {
    const pos = computePopoverPosition({
      anchorRect: new DOMRect(100, 80, 24, 24),
      panelWidth: 280,
      panelHeight: 120,
      viewportWidth: 1280,
      viewportHeight: 900,
    });
    expect(pos.top).toBe(112);
    expect(pos.left).toBeGreaterThanOrEqual(8);
    expect(pos.width).toBe(280);
  });

  it("flips above anchor when bottom overflow", () => {
    const pos = computePopoverPosition({
      anchorRect: new DOMRect(100, 850, 24, 24),
      panelWidth: 280,
      panelHeight: 200,
      viewportWidth: 1280,
      viewportHeight: 900,
    });
    expect(pos.top).toBeLessThan(850);
  });
});
