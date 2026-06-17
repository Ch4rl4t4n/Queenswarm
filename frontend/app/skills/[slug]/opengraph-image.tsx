import { marketingCoverImageResponse, marketingOgSize } from "@/lib/marketing-og-image";
import { toMarketingProductView, typeLabel } from "@/lib/marketing-catalog-view";
import { fetchMarketingProduct } from "@/lib/marketing-products";

export const alt = "Let Agents Cook product cover";
export const size = marketingOgSize;
export const contentType = "image/png";

interface ProductOgImageProps {
  params: Promise<{ slug: string }>;
}

/** Per-product OG from cover.html visual system (M5). */
export default async function ProductOgImage({ params }: ProductOgImageProps): Promise<Response> {
  const { slug } = await params;
  const product = await fetchMarketingProduct(slug);
  if (!product) {
    return marketingCoverImageResponse({
      title: "Product not found",
      hook: "Browse verified skills at letagentscook.org/skills",
      kindLabel: "Catalog",
      priceLabel: "letagentscook.org",
    });
  }

  const view = toMarketingProductView(product);
  return marketingCoverImageResponse({
    title: view.title,
    hook: view.summary,
    kindLabel: typeLabel(view.type),
    priceLabel: view.priceLabel,
    badge: view.scorecardClean ? "SCORECARD 100" : "VERIFIED",
  });
}
