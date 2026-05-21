/** Resolved tenant white-label branding for shell chrome. */

export interface TenantBrandingBrief {
  brand_name: string;
  logo_url?: string | null;
  accent_hex: string;
  hide_platform_branding: boolean;
  tagline: string;
}

export const DEFAULT_HIVE_BRAND = {
  brand_name: "QueenSwarm",
  logo_url: null as string | null,
  accent_hex: "#FFB800",
  hide_platform_branding: false,
  tagline: "HIVE CONTROL · V4",
} satisfies TenantBrandingBrief;

export function resolveTenantBranding(
  raw: Partial<TenantBrandingBrief> | null | undefined,
): TenantBrandingBrief {
  if (!raw?.brand_name?.trim()) {
    return DEFAULT_HIVE_BRAND;
  }
  return {
    brand_name: raw.brand_name.trim(),
    logo_url: raw.logo_url ?? null,
    accent_hex: raw.accent_hex || DEFAULT_HIVE_BRAND.accent_hex,
    hide_platform_branding: Boolean(raw.hide_platform_branding),
    tagline: raw.tagline?.trim() || DEFAULT_HIVE_BRAND.tagline,
  };
}

export function isCustomTenantBranding(raw: TenantBrandingBrief | null | undefined): boolean {
  if (!raw) {
    return false;
  }
  return Boolean(
    raw.hide_platform_branding ||
      raw.logo_url ||
      (raw.brand_name && raw.brand_name !== DEFAULT_HIVE_BRAND.brand_name),
  );
}
