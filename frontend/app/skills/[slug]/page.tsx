import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { ProductDetailView } from "@/components/marketing/product-detail-view";
import { marketingPublicOrigin } from "@/lib/marketing-host";
import { toMarketingProductView } from "@/lib/marketing-catalog-view";
import { fetchMarketingCatalog, fetchMarketingProduct } from "@/lib/marketing-products";

interface SkillDetailPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: SkillDetailPageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await fetchMarketingProduct(slug);
  if (!product) {
    return { title: "Product not found · Let Agents Cook" };
  }
  const origin = marketingPublicOrigin();
  const ogPath = `/skills/${encodeURIComponent(slug)}/opengraph-image`;
  return {
    title: `${product.title} · Let Agents Cook`,
    description: product.subtitle,
    openGraph: {
      title: product.title,
      description: product.subtitle,
      type: "website",
      url: `${origin}/skills/${slug}`,
      images: [{ url: ogPath, width: 1200, height: 630, alt: product.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: product.title,
      description: product.subtitle,
      images: [ogPath],
    },
  };
}

export default async function SkillDetailPage({ params }: SkillDetailPageProps): Promise<JSX.Element> {
  const { slug } = await params;
  const product = await fetchMarketingProduct(slug);
  if (!product) {
    notFound();
  }

  const catalog = await fetchMarketingCatalog();
  const views = catalog.products.map(toMarketingProductView);
  const view = toMarketingProductView(product);
  const related = views
    .filter((item) => item.slug !== view.slug && item.niches.some((niche) => view.niches.includes(niche)))
    .slice(0, 3);

  return (
    <MarketingShell>
      <ProductDetailView product={view} related={related} />
    </MarketingShell>
  );
}
