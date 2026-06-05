import type { Metadata } from "next";
import Link from "next/link";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { appPublicOrigin } from "@/lib/marketing-host";
import { fetchMarketingProduct } from "@/lib/marketing-products";

export const metadata: Metadata = {
  title: "Get started · Let Agents Cook",
  description: "Bridge from purchase to Queenswarm harness runtime.",
};

interface StartPageProps {
  searchParams: Promise<{ product?: string }>;
}

export default async function StartPage({ searchParams }: StartPageProps): Promise<JSX.Element> {
  const params = await searchParams;
  const slug = params.product?.trim() ?? "";
  const product = slug ? await fetchMarketingProduct(slug) : null;
  const appOrigin = appPublicOrigin();
  const loginHref = slug
    ? `${appOrigin}/login?next=${encodeURIComponent(`/apps-tools/skill-factory?product=${slug}`)}`
    : `${appOrigin}/login`;

  return (
    <MarketingShell>
      <section className="mx-auto max-w-2xl px-4 py-16">
        <p className="text-xs uppercase tracking-[0.2em] text-pollen">Post-purchase</p>
        <h1 className="mt-3 font-[family-name:var(--font-hive-display)] text-3xl font-bold">
          Run your purchase inside Queenswarm
        </h1>
        <p className="mt-4 text-sm text-(--qs-text-2)">
          {product
            ? `You bought or selected "${product.title}". Log in to import the bundle, run simulate-first checks, and deploy the harness.`
            : "Log in to Queenswarm to import your bundle and run simulate-first checks before live use."}
        </p>
        <ol className="mt-8 list-decimal space-y-2 pl-5 text-sm text-(--qs-text-2)">
          <li>Log in to Queenswarm</li>
          <li>Open Skill Factory or Content Factory</li>
          <li>Import the bundle and run the readiness smoke test</li>
          <li>Execute only after simulation passes</li>
        </ol>
        <div className="mt-10 flex flex-wrap gap-3">
          <a href={loginHref} className="qs-btn qs-btn--primary">
            Continue to Queenswarm
          </a>
          <Link href="/skills" className="qs-btn qs-btn--ghost">
            Back to catalog
          </Link>
        </div>
      </section>
    </MarketingShell>
  );
}
