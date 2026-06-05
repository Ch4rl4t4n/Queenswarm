import Link from "next/link";

import type { MarketingProduct } from "@/lib/marketing-products";

interface ProductCardProps {
  readonly product: MarketingProduct;
}

function kindLabel(kind: string): string {
  if (kind === "content_pack") {
    return "Content pack";
  }
  return "Verified skill";
}

export function ProductCard({ product }: ProductCardProps): JSX.Element {
  return (
    <article className="v4-card v4-card-tight flex h-full flex-col gap-3 border border-(--qs-border) p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-(--qs-text-3)">{kindLabel(product.kind)}</p>
        {product.featured ? <span className="v4-badge v4-badge--gold text-[10px]">featured</span> : null}
      </div>
      <h2 className="font-[family-name:var(--font-hive-display)] text-lg font-semibold leading-snug text-(--qs-text)">
        <Link href={`/skills/${product.slug}`} className="hover:text-pollen">
          {product.title}
        </Link>
      </h2>
      <p className="line-clamp-3 text-sm text-(--qs-text-2)">{product.subtitle}</p>
      <div className="mt-auto flex items-center justify-between gap-3 pt-2">
        <span className="font-mono text-sm text-pollen">{product.price || "€9.00"}</span>
        <Link href={`/skills/${product.slug}`} className="qs-btn qs-btn--ghost qs-btn--sm">
          View details
        </Link>
      </div>
    </article>
  );
}
