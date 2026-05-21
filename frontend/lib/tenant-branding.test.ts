import { describe, expect, it } from "vitest";

import { DEFAULT_HIVE_BRAND, isCustomTenantBranding, resolveTenantBranding } from "@/lib/tenant-branding";

describe("tenant-branding", () => {
  it("returns default when branding missing", () => {
    expect(resolveTenantBranding(null)).toEqual(DEFAULT_HIVE_BRAND);
  });

  it("detects custom branding overrides", () => {
    expect(
      isCustomTenantBranding({
        brand_name: "Acme Hive",
        accent_hex: "#00FFFF",
        hide_platform_branding: false,
        tagline: "HIVE CONTROL",
      }),
    ).toBe(true);
  });

  it("merges tenant brand fields", () => {
    const brand = resolveTenantBranding({
      brand_name: " Acme ",
      logo_url: "https://cdn.test/logo.png",
      accent_hex: "#112233",
      hide_platform_branding: true,
      tagline: "CUSTOM",
    });
    expect(brand.brand_name).toBe("Acme");
    expect(brand.logo_url).toContain("logo.png");
  });
});
