import { marketingCoverImageResponse, marketingOgSize } from "@/lib/marketing-og-image";

export const alt = "Let Agents Cook — verified agent skills";
export const size = marketingOgSize;
export const contentType = "image/png";

/** Marketing home OG — cover.html neon-dark brand (M5). */
export default function MarketingHomeOgImage() {
  return marketingCoverImageResponse({
    title: "Let Agents Cook",
    hook: "Buy verified agent skills and content packs — simulate-first, quality-scored, sold on trusted marketplaces.",
    kindLabel: "Verified catalog",
    priceLabel: "letagentscook.org",
    badge: "SIMULATE-FIRST",
  });
}
