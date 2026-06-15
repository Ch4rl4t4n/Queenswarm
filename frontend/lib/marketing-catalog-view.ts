import type { MarketingProduct } from "@/lib/marketing-products";

export const MARKETING_NICHES = [
  "Newsletter",
  "SEO",
  "Instagram",
  "LinkedIn",
  "Facebook Ads",
  "Email",
  "Coaching",
  "B2B SaaS",
  "E-commerce",
  "Local Services",
  "Content",
  "Growth",
] as const;

export type MarketingNiche = (typeof MARKETING_NICHES)[number];

export type MarketingProductType = "skill" | "pack";

export interface MarketingProductView {
  slug: string;
  title: string;
  type: MarketingProductType;
  price: number;
  priceLabel: string;
  score: number | null;
  scorecardVerdict: string | null;
  scorecardClean: boolean;
  featured: boolean;
  status: "listed" | "soon";
  gumroad: string | null;
  niches: MarketingNiche[];
  summary: string;
  description: string;
  whatYouGet: string[];
}

const NICHE_KEYWORDS: Record<MarketingNiche, string[]> = {
  Newsletter: ["newsletter"],
  SEO: ["seo"],
  Instagram: ["instagram"],
  LinkedIn: ["linkedin"],
  "Facebook Ads": ["facebook", "ad copy"],
  Email: ["email", "cold email"],
  Coaching: ["coach"],
  "B2B SaaS": ["b2b", "saas"],
  "E-commerce": ["e-commerce", "ecommerce", "product description"],
  "Local Services": ["local services"],
  Content: ["content", "blog", "social", "thread", "youtube", "tiktok", "webinar"],
  Growth: ["growth", "lead magnet", "launch"],
};

function parsePriceAmount(price: string): number {
  const match = price.match(/€\s*([\d.]+)/);
  if (!match) {
    return 9;
  }
  return Number.parseFloat(match[1] ?? "9");
}

function inferNiches(product: MarketingProduct): MarketingNiche[] {
  const hay = `${product.slug} ${product.title} ${product.subtitle}`.toLowerCase();
  const hits = MARKETING_NICHES.filter((niche) =>
    NICHE_KEYWORDS[niche].some((keyword) => hay.includes(keyword)),
  );
  if (hits.length > 0) {
    return hits.slice(0, 3);
  }
  if (product.kind === "content_pack") {
    return ["Content"];
  }
  return ["Growth"];
}

function defaultWhatYouGet(type: MarketingProductType): string[] {
  if (type === "pack") {
    return [
      "Ready-to-use content templates and scripts",
      "Simulate-first usage notes and guardrails",
      "Listing copy and cover assets",
      "Niche-tuned examples you can adapt",
      "Downloadable bundle — yours after purchase",
    ];
  }
  return [
    "Agent / skill definition (drop-in)",
    "Simulate-first dry-run harness",
    "Explicit guardrails and evaluation criteria",
    "Listing copy and cover assets",
    "Downloadable bundle — yours after purchase",
  ];
}

/** Map API catalog row to Claude Design card/detail view model. */
export function toMarketingProductView(product: MarketingProduct): MarketingProductView {
  const type: MarketingProductType = product.kind === "content_pack" ? "pack" : "skill";
  const gumroad = product.gumroad_url?.trim() || null;
  const listed = Boolean(gumroad?.startsWith("http"));

  return {
    slug: product.slug,
    title: product.title,
    type,
    price: parsePriceAmount(product.price),
    priceLabel: product.price || "€9.00",
    score: product.score > 0 ? product.score : null,
    scorecardVerdict: product.scorecard_verdict || null,
    scorecardClean: Boolean(product.scorecard_clean),
    featured: product.featured,
    status: listed ? "listed" : "soon",
    gumroad: listed ? gumroad : null,
    niches: inferNiches(product),
    summary: product.subtitle,
    description: product.subtitle,
    whatYouGet: defaultWhatYouGet(type),
  };
}

export function typeLabel(type: MarketingProductType): string {
  return type === "skill" ? "Verified skill" : "Content pack";
}

export function formatCompactCount(value: number | null | undefined): string {
  if (value == null) {
    return "";
  }
  if (value >= 1000) {
    const compact = value / 1000;
    return `${compact % 1 === 0 ? compact.toFixed(0) : compact.toFixed(1).replace(".0", "")}k`;
  }
  return String(value);
}
