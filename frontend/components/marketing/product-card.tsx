"use client";

import Link from "next/link";

import { CoverArt } from "@/components/marketing/cover-art";
import { LacIcon } from "@/components/marketing/lac-icons";
import { ScorePill } from "@/components/marketing/score-pill";
import { typeLabel, type MarketingProductView } from "@/lib/marketing-catalog-view";

interface ProductCardProps {
  readonly product: MarketingProductView;
  readonly compareOn?: boolean;
  readonly compareList?: string[];
  readonly onToggleCompare?: (slug: string) => void;
}

export function ProductCard({
  product,
  compareOn = false,
  compareList = [],
  onToggleCompare,
}: ProductCardProps): JSX.Element {
  const inCompare = compareList.includes(product.slug);
  const compareFull = compareList.length >= 3 && !inCompare;
  const href = `/skills/${product.slug}`;

  return (
    <Link
      href={href}
      className={`mk-card${product.featured ? " featured" : ""}`}
      style={{ textDecoration: "none", color: "inherit" }}
    >
      <div className="mk-card-top">
        <span className={`mk-type ${product.type}`}>
          <LacIcon name={product.type === "skill" ? "shield" : "doc"} size={12} />
          {typeLabel(product.type)}
        </span>
        {product.featured ? <span className="mk-corner featured">Featured</span> : null}
      </div>

      <CoverArt product={product} />

      <div className="mk-card-title">{product.title}</div>

      <div className="mk-card-tags">
        {product.niches.slice(0, 3).map((niche) => (
          <span key={niche} className="mk-tag">
            {niche}
          </span>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      <div className="mk-card-foot">
        <div className="row gap-3" style={{ alignItems: "center" }}>
          {product.status === "listed" ? (
            <span className="mk-price">€{product.price.toFixed(2)}</span>
          ) : (
            <span className="mk-soon-label">
              <span className="d" />
              Listing soon
            </span>
          )}
          <ScorePill score={product.score} />
        </div>
        {compareOn && onToggleCompare ? (
          <label
            className="mk-compare"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
            }}
            title={compareFull ? "Max 3" : "Compare"}
          >
            <input
              type="checkbox"
              checked={inCompare}
              disabled={compareFull}
              onChange={() => onToggleCompare(product.slug)}
            />
            Compare
          </label>
        ) : null}
      </div>
    </Link>
  );
}
