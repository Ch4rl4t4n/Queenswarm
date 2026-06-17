import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { MarketingHome } from "@/components/marketing/marketing-home";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { toMarketingProductView } from "@/lib/marketing-catalog-view";
import { isMarketingSiteRequest, marketingPublicOrigin } from "@/lib/marketing-host";
import { fetchMarketingCatalog } from "@/lib/marketing-products";

export const metadata: Metadata = {
  title: "Let Agents Cook — Verified agent skills",
  description:
    "Buy verified agent skills and content packs — simulate-first, quality-scored, sold on trusted marketplaces.",
  openGraph: {
    title: "Let Agents Cook — Verified agent skills",
    description:
      "Buy verified agent skills and content packs — simulate-first, quality-scored, sold on trusted marketplaces.",
    type: "website",
    url: marketingPublicOrigin(),
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Let Agents Cook" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Let Agents Cook",
    description: "Verified agent skills and content packs — simulate-first.",
    images: ["/opengraph-image"],
  },
};

export default async function RootPage(): Promise<JSX.Element> {
  const headerStore = await headers();
  const host = headerStore.get("host");
  const e2eMarketing = headerStore.get("x-e2e-marketing-site");
  if (!isMarketingSiteRequest(host, e2eMarketing)) {
    redirect(hiveOverviewHref());
  }

  const catalog = await fetchMarketingCatalog();
  const products = catalog.products.map(toMarketingProductView);

  return (
    <MarketingShell>
      <MarketingHome products={products} productCount={catalog.product_count} />
    </MarketingShell>
  );
}
