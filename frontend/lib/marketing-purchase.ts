import type { MarketingProduct } from "@/lib/marketing-products";

export interface MarketplaceLink {
  readonly id: "gumroad";
  readonly label: string;
  readonly href: string;
}

/** External purchase links for a catalog product (marketing site is promo-only). */
export function marketplaceLinksForProduct(product: MarketingProduct): MarketplaceLink[] {
  const links: MarketplaceLink[] = [];
  const gumroad = product.gumroad_url?.trim();
  if (gumroad?.startsWith("http")) {
    links.push({ id: "gumroad", label: "Gumroad", href: gumroad });
  }
  return links;
}

export function hasMarketplaceLink(product: MarketingProduct): boolean {
  return marketplaceLinksForProduct(product).length > 0;
}
