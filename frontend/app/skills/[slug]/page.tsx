import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { hasMarketplaceLink, marketplaceLinksForProduct } from "@/lib/marketing-purchase";
import { fetchMarketingProduct } from "@/lib/marketing-products";

interface SkillDetailPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: SkillDetailPageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await fetchMarketingProduct(slug);
  if (!product) {
    return { title: "Product not found · Let Agents Cook" };
  }
  return {
    title: `${product.title} · Let Agents Cook`,
    description: product.subtitle,
  };
}

export default async function SkillDetailPage({ params }: SkillDetailPageProps): Promise<JSX.Element> {
  const { slug } = await params;
  const product = await fetchMarketingProduct(slug);
  if (!product) {
    notFound();
  }

  const purchaseLinks = marketplaceLinksForProduct(product);
  const listed = hasMarketplaceLink(product);

  return (
    <MarketingShell>
      <section className="mx-auto max-w-3xl px-4 py-12">
        <Link href="/skills" className="text-sm text-(--qs-text-3) hover:text-data">
          ← Back to catalog
        </Link>
        <p className="mt-6 text-xs uppercase tracking-[0.2em] text-pollen">
          {product.kind === "content_pack" ? "Content pack" : "Verified skill"}
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-hive-display)] text-3xl font-bold md:text-4xl">
          {product.title}
        </h1>
        <p className="mt-4 text-base text-(--qs-text-2)">{product.subtitle}</p>

        <dl className="mt-8 grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
          <div className="rounded-xl border border-(--qs-border) bg-white/5 p-4">
            <dt className="text-[10px] uppercase text-(--qs-text-3)">Price anchor</dt>
            <dd className="mt-1 font-mono text-lg text-pollen">{product.price || "€9.00"}</dd>
          </div>
          <div className="rounded-xl border border-(--qs-border) bg-white/5 p-4">
            <dt className="text-[10px] uppercase text-(--qs-text-3)">Quality score</dt>
            <dd className="mt-1 font-mono text-lg text-data">{product.score}/100</dd>
          </div>
          <div className="rounded-xl border border-(--qs-border) bg-white/5 p-4">
            <dt className="text-[10px] uppercase text-(--qs-text-3)">Delivery</dt>
            <dd className="mt-1 text-(--qs-text)">Harness + guardrails</dd>
          </div>
        </dl>

        <ul className="mt-8 space-y-2 text-sm text-(--qs-text-2)">
          <li>Simulate-first workflow with explicit guardrails</li>
          <li>Bundle includes SKILL/HARNESS files and listing copy</li>
          <li>Download and use from your marketplace purchase — no app signup required</li>
        </ul>

        <div className="mt-10 rounded-xl border border-(--qs-border) bg-(--qs-surface-3)/50 p-5">
          <h2 className="font-[family-name:var(--font-hive-display)] text-lg font-semibold">Where to buy</h2>
          {listed ? (
            <>
              <p className="mt-2 text-sm text-(--qs-text-2)">
                Purchase on an external marketplace. You receive the full bundle after checkout.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                {purchaseLinks.map((link) => (
                  <a
                    key={link.id}
                    href={link.href}
                    className="qs-btn qs-btn--primary"
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    Buy on {link.label}
                  </a>
                ))}
              </div>
            </>
          ) : (
            <p className="mt-2 text-sm text-(--qs-text-2)">
              This listing is not on a marketplace yet. Check back soon — purchase links appear here after publish.
            </p>
          )}
        </div>
      </section>
    </MarketingShell>
  );
}
