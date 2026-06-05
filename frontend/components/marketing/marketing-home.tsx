import Link from "next/link";

import { CoverArt } from "@/components/marketing/cover-art";
import { LacIcon } from "@/components/marketing/lac-icons";
import { ProductCard } from "@/components/marketing/product-card";
import { ScorePill } from "@/components/marketing/score-pill";
import { typeLabel, type MarketingProductView } from "@/lib/marketing-catalog-view";

interface MarketingHomeProps {
  readonly products: MarketingProductView[];
  readonly productCount: number;
}

function MarketingHero({ products, productCount }: MarketingHomeProps): JSX.Element {
  const hero =
    products.find((item) => item.featured && item.status === "listed") ??
    products.find((item) => item.featured) ??
    products[0];

  return (
    <section className="mk-hero">
      <div className="mk-wrap">
        <div className="mk-hero-grid">
          <div className="mk-rise">
            <span className="mk-eyebrow">
              <LacIcon name="shield" size={13} />
              Verified · Simulate-first
            </span>
            <h1 className="mk-h1">
              Verified agent skills,
              <br />
              ready to <span className="wordmark-grad">cook</span>.
            </h1>
            <p className="mk-lede">
              A curated marketplace of agent skills and content packs — each one simulate-first, quality-scored, and
              delivered through trusted marketplaces. Buy once, own it forever.
            </p>
            <div className="mk-hero-cta">
              <Link href="/skills" className="btn btn-gold btn-lg">
                Browse the catalog <LacIcon name="arrow" size={17} />
              </Link>
              <Link href="/how-it-works" className="btn btn-secondary btn-lg">
                How it works
              </Link>
            </div>
            <div className="mk-hero-stats">
              <div className="mk-hero-stat">
                <div className="n gold">{productCount}</div>
                <div className="l">Skills &amp; packs</div>
              </div>
              <div className="mk-hero-stat">
                <div className="n">100%</div>
                <div className="l">Simulate-first verified</div>
              </div>
              <div className="mk-hero-stat">
                <div className="n">€9+</div>
                <div className="l">One-time, own forever</div>
              </div>
            </div>
          </div>

          {hero ? (
            <div className="mk-hero-art mk-rise" style={{ animationDelay: "0.1s" }}>
              <div className="mk-float-card">
                <div className="mk-card-top">
                  <span className={`mk-type ${hero.type}`}>
                    <LacIcon name={hero.type === "skill" ? "shield" : "doc"} size={12} />
                    {typeLabel(hero.type)}
                  </span>
                  <span className="mk-corner featured">Featured</span>
                </div>
                <CoverArt product={hero} />
                <div className="mk-card-title" style={{ fontSize: 17 }}>
                  {hero.title}
                </div>
                <div className="mk-card-tags">
                  {hero.niches.map((niche) => (
                    <span key={niche} className="mk-tag">
                      {niche}
                    </span>
                  ))}
                </div>
                <div className="mk-card-foot">
                  <div className="row gap-3">
                    <span className="mk-price">€{hero.price.toFixed(2)}</span>
                    <ScorePill score={hero.score} />
                  </div>
                  <Link href={`/skills/${hero.slug}`} className="btn btn-primary">
                    View
                  </Link>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function TrustStrip(): JSX.Element {
  const items = [
    {
      ic: "flask" as const,
      h: "Simulate-first",
      p: "Every skill is dry-run-able. See projected outcomes before anything goes live.",
    },
    {
      ic: "spark" as const,
      h: "Quality scored",
      p: "Each listing carries a transparent quality score from its verification run.",
    },
    {
      ic: "shield" as const,
      h: "Guardrails built in",
      p: "Skills refuse off-brief or low-quality output instead of shipping it anyway.",
    },
    {
      ic: "tag" as const,
      h: "Own it forever",
      p: "One-time purchase through trusted marketplaces. No subscriptions, no lock-in.",
    },
  ];

  return (
    <section className="mk-section" style={{ paddingTop: 24 }}>
      <div className="mk-wrap">
        <div className="mk-trust-strip">
          {items.map((item, index) => (
            <div key={item.h} className="mk-trust-card mk-rise" style={{ animationDelay: `${index * 0.05}s` }}>
              <div className="ic" style={{ color: "oklch(0.85 0.12 295)" }}>
                <LacIcon name={item.ic} size={20} />
              </div>
              <h4>{item.h}</h4>
              <p>{item.p}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturedSection({ products }: { readonly products: MarketingProductView[] }): JSX.Element {
  const featured = products.filter((product) => product.featured);

  return (
    <section className="mk-section">
      <div className="mk-wrap">
        <div className="mk-sec-head">
          <div>
            <div className="mk-sec-title">Featured skills</div>
            <div className="mk-sec-sub">Hand-picked, verified, and live now.</div>
          </div>
          <Link href="/skills" className="mk-sec-link">
            View all <LacIcon name="arrow" size={15} />
          </Link>
        </div>
        <div className="mk-grid">
          {featured.map((product) => (
            <ProductCard key={product.slug} product={product} />
          ))}
        </div>
      </div>
    </section>
  );
}

function BundleSection({ products }: { readonly products: MarketingProductView[] }): JSX.Element {
  const bundleCandidates = products.filter((product) =>
    ["newsletter", "seo", "lead-magnet", "instagram"].some((token) => product.slug.includes(token)),
  ).slice(0, 3);

  return (
    <section className="mk-section" style={{ paddingTop: 0 }}>
      <div className="mk-wrap">
        <div className="mk-bundle">
          <span className="mk-bundle-soon">Coming soon</span>
          <div
            style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 28, alignItems: "center" }}
            className="bundle-inner"
          >
            <div>
              <span className="mk-eyebrow">
                <LacIcon name="bolt" size={13} />
                Starter bundle
              </span>
              <h3 style={{ fontSize: 26, fontWeight: 800, margin: "14px 0 10px", letterSpacing: "-0.01em" }}>
                The Creator Growth Starter
              </h3>
              <p className="text-2" style={{ fontSize: 15, lineHeight: 1.6, maxWidth: 460 }}>
                Three of our highest-scoring skills, bundled for one price. Newsletter loop, SEO pipeline and content
                packs — everything to build an audience that compounds.
              </p>
              <div className="row gap-3 mt-6" style={{ alignItems: "center", flexWrap: "wrap" }}>
                <button type="button" className="btn btn-coming" style={{ width: "auto", padding: "12px 18px" }} disabled>
                  <LacIcon name="bolt" size={15} />
                  Bundle pricing — coming soon
                </button>
                <span className="text-3 fs-13">Save vs. buying separately</span>
              </div>
            </div>
            <div className="col gap-3 bundle-cards">
              {bundleCandidates.map((product) => (
                <div key={product.slug} className="glass-light" style={{ padding: 14, display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ color: "oklch(0.85 0.12 295)", flexShrink: 0 }}>
                    <LacIcon name={product.type === "skill" ? "hexagon" : "doc"} size={22} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div className="fw-600 fs-13" style={{ lineHeight: 1.3 }}>
                      {product.title}
                    </div>
                    <div className="text-3 fs-12 mt-1">
                      Score {product.score} · €{product.price.toFixed(2)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function MarketingHome({ products, productCount }: MarketingHomeProps): JSX.Element {
  return (
    <>
      <MarketingHero products={products} productCount={productCount} />
      <TrustStrip />
      <FeaturedSection products={products} />
      <BundleSection products={products} />
    </>
  );
}
