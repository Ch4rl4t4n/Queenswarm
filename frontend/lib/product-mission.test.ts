import { describe, expect, it } from "vitest";

import { buildProductMissionBrief } from "@/lib/product-mission";

describe("buildProductMissionBrief", () => {
  it("includes default niche when hint empty", () => {
    const brief = buildProductMissionBrief();
    expect(brief).toContain("Product Mission — Revenue Swarm Factory");
    expect(brief).toContain("Niche hint:");
    expect(brief).toContain("newsletter");
  });

  it("uses custom niche hint when provided", () => {
    const brief = buildProductMissionBrief("crypto trading alerts");
    expect(brief).toContain("Niche hint: crypto trading alerts");
  });
});
