"use client";

import { useEffect, useMemo, useState } from "react";

import { LacIcon } from "@/components/marketing/lac-icons";
import { ProductCard } from "@/components/marketing/product-card";
import { MARKETING_NICHES, type MarketingProductView } from "@/lib/marketing-catalog-view";

interface CatalogPageClientProps {
  readonly products: MarketingProductView[];
}

const PAGE_SIZE = 9;

const TYPE_FILTERS = [
  { key: "all", label: "All types" },
  { key: "skill", label: "Verified skill" },
  { key: "pack", label: "Content pack" },
] as const;

function CompareBar({
  compareList,
  products,
  onClear,
  onRemove,
}: {
  readonly compareList: string[];
  readonly products: MarketingProductView[];
  readonly onClear: () => void;
  readonly onRemove: (slug: string) => void;
}): JSX.Element | null {
  if (compareList.length === 0) {
    return null;
  }
  const items = compareList
    .map((slug) => products.find((product) => product.slug === slug))
    .filter((product): product is MarketingProductView => Boolean(product));

  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 90,
        background: "rgba(10,14,35,0.95)",
        backdropFilter: "blur(16px)",
        border: "1px solid var(--border-3)",
        borderRadius: 16,
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        gap: 14,
        boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
        maxWidth: "calc(100vw - 32px)",
        flexWrap: "wrap",
      }}
    >
      <span className="fw-600 fs-13" style={{ color: "var(--text-2)" }}>
        Compare ({items.length}/3)
      </span>
      <div className="row gap-2" style={{ flexWrap: "wrap" }}>
        {items.map((product) => (
          <span key={product.slug} className="mk-tag" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {product.title.slice(0, 22)}
            {product.title.length > 22 ? "…" : ""}
            <button
              type="button"
              style={{ cursor: "pointer", opacity: 0.6, background: "none", border: "none", color: "inherit", padding: 0 }}
              onClick={() => onRemove(product.slug)}
              aria-label={`Remove ${product.title} from compare`}
            >
              <LacIcon name="close" size={12} />
            </button>
          </span>
        ))}
      </div>
      <button type="button" className="btn btn-primary" style={{ padding: "8px 14px" }} disabled={items.length < 2}>
        Compare
      </button>
      <button type="button" className="btn btn-ghost" style={{ padding: "8px 10px" }} onClick={onClear}>
        Clear
      </button>
    </div>
  );
}

export function CatalogPageClient({ products }: CatalogPageClientProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<(typeof TYPE_FILTERS)[number]["key"]>("all");
  const [niche, setNiche] = useState<string>("all");
  const [sort, setSort] = useState("featured");
  const [page, setPage] = useState(1);
  const [compareOn, setCompareOn] = useState(false);
  const [compareList, setCompareList] = useState<string[]>([]);

  const filtered = useMemo(() => {
    let list = products.filter((product) => {
      if (typeFilter !== "all" && product.type !== typeFilter) {
        return false;
      }
      if (niche !== "all" && !product.niches.includes(niche as (typeof MARKETING_NICHES)[number])) {
        return false;
      }
      if (query.trim()) {
        const hay = `${product.title} ${product.summary} ${product.niches.join(" ")}`.toLowerCase();
        if (!hay.includes(query.toLowerCase())) {
          return false;
        }
      }
      return true;
    });

    list = [...list].sort((left, right) => {
      if (sort === "featured") {
        return Number(right.featured) - Number(left.featured) || (right.score ?? 0) - (left.score ?? 0);
      }
      if (sort === "score") {
        return (right.score ?? 0) - (left.score ?? 0);
      }
      if (sort === "price-asc") {
        return left.price - right.price;
      }
      if (sort === "price-desc") {
        return right.price - left.price;
      }
      if (sort === "title") {
        return left.title.localeCompare(right.title);
      }
      return 0;
    });
    return list;
  }, [products, query, typeFilter, niche, sort]);

  useEffect(() => {
    setPage(1);
  }, [query, typeFilter, niche, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleCompare = (slug: string): void => {
    setCompareList((list) =>
      list.includes(slug) ? list.filter((item) => item !== slug) : list.length < 3 ? [...list, slug] : list,
    );
  };

  const reset = (): void => {
    setQuery("");
    setTypeFilter("all");
    setNiche("all");
  };

  return (
    <div className="mk-wrap" style={{ paddingTop: 40, paddingBottom: 70 }}>
      <div className="mk-sec-head" style={{ marginBottom: 22 }}>
        <div>
          <div className="mk-sec-title">Skill catalog</div>
          <div className="mk-sec-sub">
            {filtered.length} verified {filtered.length === 1 ? "listing" : "listings"} · skills &amp; content packs
          </div>
        </div>
        <label className="mk-compare" style={{ fontSize: 13 }}>
          <input
            type="checkbox"
            checked={compareOn}
            onChange={(event) => {
              setCompareOn(event.target.checked);
              if (!event.target.checked) {
                setCompareList([]);
              }
            }}
          />
          Compare mode
        </label>
      </div>

      <div className="mk-filterbar">
        <div className="mk-search-row">
          <div className="mk-search">
            <LacIcon name="search" size={18} />
            <input
              placeholder="Search skills, packs, niches…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <select className="mk-select" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="featured">Sort: Featured</option>
            <option value="score">Highest score</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
            <option value="title">A–Z</option>
          </select>
        </div>
        <div className="mk-chips">
          {TYPE_FILTERS.map((filter) => (
            <button
              key={filter.key}
              type="button"
              className={`mk-chip${typeFilter === filter.key ? " active" : ""}`}
              onClick={() => setTypeFilter(filter.key)}
            >
              {filter.label}
            </button>
          ))}
          <span style={{ width: 1, background: "var(--border-2)", margin: "0 4px" }} />
          <button
            type="button"
            className={`mk-chip${niche === "all" ? " active" : ""}`}
            onClick={() => setNiche("all")}
          >
            All niches
          </button>
          {MARKETING_NICHES.map((item) => (
            <button
              key={item}
              type="button"
              className={`mk-chip${niche === item ? " active" : ""}`}
              onClick={() => setNiche(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {pageItems.length === 0 ? (
        <div className="mk-empty">
          <div className="glyph" style={{ color: "var(--text-3)" }}>
            <LacIcon name="search" size={64} />
          </div>
          <h3>No skills match those filters</h3>
          <p>Try a different niche or clear your search — new skills are added regularly.</p>
          <button type="button" className="btn btn-secondary mt-4" onClick={reset}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="mk-grid">
          {pageItems.map((product) => (
            <ProductCard
              key={product.slug}
              product={product}
              compareOn={compareOn}
              compareList={compareList}
              onToggleCompare={toggleCompare}
            />
          ))}
        </div>
      )}

      {totalPages > 1 ? (
        <div className="mk-pagination">
          <button type="button" className="mk-page-btn" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>
            ‹
          </button>
          {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
            <button
              key={pageNumber}
              type="button"
              className={`mk-page-btn${pageNumber === page ? " active" : ""}`}
              onClick={() => setPage(pageNumber)}
            >
              {pageNumber}
            </button>
          ))}
          <button
            type="button"
            className="mk-page-btn"
            disabled={page === totalPages}
            onClick={() => setPage((value) => value + 1)}
          >
            ›
          </button>
        </div>
      ) : null}

      {compareOn ? (
        <CompareBar
          compareList={compareList}
          products={products}
          onClear={() => setCompareList([])}
          onRemove={toggleCompare}
        />
      ) : null}
    </div>
  );
}
