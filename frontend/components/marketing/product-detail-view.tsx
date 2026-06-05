"use client";

import Link from "next/link";
import { useState } from "react";

import { LacIcon } from "@/components/marketing/lac-icons";
import { ProductCard } from "@/components/marketing/product-card";
import { ScorePill } from "@/components/marketing/score-pill";
import { typeLabel, type MarketingProductView } from "@/lib/marketing-catalog-view";

interface ProductDetailViewProps {
  readonly product: MarketingProductView;
  readonly related: MarketingProductView[];
}

function PurchasePanel({ product }: { readonly product: MarketingProductView }): JSX.Element {
  const listed = product.status === "listed" && product.gumroad;

  return (
    <aside className="mk-purchase">
      <div className="mk-purchase-card">
        <div className="row between" style={{ alignItems: "flex-start" }}>
          <span className={`mk-type ${product.type}`}>
            <LacIcon name={product.type === "skill" ? "shield" : "doc"} size={12} />
            {typeLabel(product.type)}
          </span>
          <ScorePill score={product.score} />
        </div>

        <div style={{ marginTop: 18 }}>
          {listed ? (
            <div className="mk-purchase-price">
              €{product.price.toFixed(2)}
              <small>one-time</small>
            </div>
          ) : (
            <div className="mk-purchase-price" style={{ color: "var(--text-2)", fontSize: 26 }}>
              €{product.price.toFixed(2)}
              <small>at launch</small>
            </div>
          )}
        </div>

        <div className="mk-buy-row">
          {listed ? (
            <a className="btn btn-primary btn-block" href={product.gumroad ?? "#"} target="_blank" rel="noopener noreferrer">
              Buy on Gumroad <LacIcon name="external" size={16} />
            </a>
          ) : (
            <div className="mk-soon-panel">
              <div className="t">Listing soon</div>
              <div className="d">This skill is in final verification. Check back when the marketplace link goes live.</div>
            </div>
          )}
          <button type="button" className="btn-coming" disabled>
            <LacIcon name="external" size={15} />
            More marketplaces — coming soon
          </button>
        </div>

        <div className="mk-trust-list">
          <div className="mk-trust-item">
            <LacIcon name="flask" size={16} />
            <span>Simulate-first verified — outcomes checked before listing.</span>
          </div>
          <div className="mk-trust-item">
            <LacIcon name="tag" size={16} />
            <span>One-time purchase. Own it forever, no subscription.</span>
          </div>
          <div className="mk-trust-item">
            <LacIcon name="shield" size={16} />
            <span>Secure checkout handled by Gumroad.</span>
          </div>
        </div>
      </div>

      <p className="text-4 fs-12" style={{ textAlign: "center", marginTop: 14, lineHeight: 1.5 }}>
        Delivered as a download through an external marketplace. Let Agents Cook is a catalog — there&apos;s no account to
        create here.
      </p>
    </aside>
  );
}

function Gallery({ product }: { readonly product: MarketingProductView }): JSX.Element {
  const [active, setActive] = useState(0);
  const hue = product.type === "skill" ? "295" : "195";
  const labels = ["cover.html preview", "sample output", "verification report"];

  return (
    <div className="mk-gallery">
      <div
        className="mk-gallery-main"
        style={{
          background: `radial-gradient(ellipse 100% 90% at ${active === 1 ? "70" : active === 2 ? "40" : "30"}% 25%, oklch(0.42 0.18 ${hue} / 0.5), transparent 60%), linear-gradient(160deg, #0d1230, #0a0e23)`,
        }}
      >
        <div style={{ position: "relative", textAlign: "center", color: `oklch(0.85 0.12 ${hue})` }}>
          <LacIcon name={product.type === "skill" ? "hexagon" : "doc"} size={56} />
          <div className="text-3 fs-12 mt-3" style={{ fontFamily: "var(--font-mono)" }}>
            {labels[active]}
          </div>
        </div>
      </div>
      <div className="mk-gallery-thumbs">
        {[0, 1, 2].map((index) => (
          <button
            key={index}
            type="button"
            className={`mk-gthumb${active === index ? " active" : ""}`}
            onClick={() => setActive(index)}
            style={{ display: "grid", placeItems: "center", color: "var(--text-3)", background: "none", cursor: "pointer" }}
            aria-label={labels[index]}
          >
            <LacIcon name={index === 0 ? "doc" : index === 1 ? "spark" : "shield"} size={16} />
          </button>
        ))}
      </div>
    </div>
  );
}

export function ProductDetailView({ product, related }: ProductDetailViewProps): JSX.Element {
  return (
    <div className="mk-wrap">
      <div className="mk-detail-grid">
        <div>
          <div className="mk-breadcrumb">
            <Link href="/">Home</Link>
            <LacIcon name="arrow" size={13} />
            <Link href="/skills">Catalog</Link>
            <LacIcon name="arrow" size={13} />
            <span className="text-2">{typeLabel(product.type)}</span>
          </div>

          <div className="mk-detail-meta">
            <span className={`mk-type ${product.type}`}>
              <LacIcon name={product.type === "skill" ? "shield" : "doc"} size={12} />
              {typeLabel(product.type)}
            </span>
            {product.featured ? <span className="mk-corner featured">Featured</span> : null}
            {product.status === "soon" ? (
              <span className="mk-soon-label">
                <span className="d" />
                Listing soon
              </span>
            ) : null}
          </div>

          <h1 className="mk-detail-title">{product.title}</h1>
          <p className="mk-lede" style={{ marginTop: 0, marginBottom: 22 }}>
            {product.summary}
          </p>

          <Gallery product={product} />

          <div className="mk-card-tags" style={{ marginBottom: 8 }}>
            {product.niches.map((niche) => (
              <span key={niche} className="mk-tag" style={{ fontSize: 12, padding: "5px 11px" }}>
                {niche}
              </span>
            ))}
          </div>

          <div className="mk-prose">
            <h3>Overview</h3>
            <p>{product.description}</p>

            <h3>What you get</h3>
            <ul className="mk-checklist">
              {product.whatYouGet.map((item) => (
                <li key={item}>
                  <LacIcon name="check" size={18} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            <h3>Verified, not promised</h3>
            <p>
              Before this {product.type === "skill" ? "skill" : "pack"} was listed, it ran through a simulate-first
              verification pass. The quality score
              {product.score != null ? ` of ${product.score}` : ""} reflects how it performed against its brief —
              measured, not marketed.{" "}
              <Link href="/verify-first" className="gold">
                Learn about verify-first →
              </Link>
            </p>
          </div>

          {related.length > 0 ? (
            <div style={{ marginTop: 40 }}>
              <div className="mk-sec-title" style={{ fontSize: 20, marginBottom: 16 }}>
                Related skills
              </div>
              <div className="mk-grid">
                {related.map((item) => (
                  <ProductCard key={item.slug} product={item} />
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <PurchasePanel product={product} />
      </div>
    </div>
  );
}
