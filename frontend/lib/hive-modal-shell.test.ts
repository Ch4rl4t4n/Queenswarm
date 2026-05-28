/**
 * @vitest-environment happy-dom
 */
import { describe, expect, it } from "vitest";

import {
  hiveModalOverlayAlignClass,
  hiveModalBottomSheetPanelClass,
} from "@/components/hive/hive-modal-shell";

describe("hive-modal-shell", () => {
  it("maps center overlay alignment", () => {
    expect(hiveModalOverlayAlignClass("center")).toContain("items-center");
    expect(hiveModalOverlayAlignClass("center")).toContain("p-4");
  });

  it("maps bottom-sheet overlay alignment for mobile-first sheet", () => {
    const classes = hiveModalOverlayAlignClass("bottom-sheet");
    expect(classes).toContain("items-end");
    expect(classes).toContain("sm:items-center");
    expect(classes).toContain("p-0");
  });

  it("maps drawer-right overlay alignment", () => {
    const classes = hiveModalOverlayAlignClass("drawer-right");
    expect(classes).toContain("justify-end");
    expect(classes).toContain("items-stretch");
  });

  it("exports bottom-sheet panel base classes", () => {
    expect(hiveModalBottomSheetPanelClass).toContain("rounded-t-");
    expect(hiveModalBottomSheetPanelClass).toContain("qs-bubble");
  });
});
