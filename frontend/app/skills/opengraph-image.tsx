import { marketingCoverImageResponse, marketingOgSize } from "@/lib/marketing-og-image";

export const alt = "Let Agents Cook skill catalog";
export const size = marketingOgSize;
export const contentType = "image/png";

/** Catalog OG — cover.html style (M5). */
export default function SkillsCatalogOgImage() {
  return marketingCoverImageResponse({
    title: "Verified skill catalog",
    hook: "Browse agent skills and content packs with scorecard QA — buy on Gumroad and run simulate-first.",
    kindLabel: "Skill catalog",
    priceLabel: "Scorecard-clean",
    badge: "LET AGENTS COOK",
  });
}
