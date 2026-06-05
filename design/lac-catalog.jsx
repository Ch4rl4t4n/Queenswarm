// Let Agents Cook — Catalog page (FilterBar, grid, pagination, empty, compare).
// Exports: window.LACCatalog
const { useState: useStateCat, useMemo } = React;

function FilterBar({ query, setQuery, typeFilter, setTypeFilter, niche, setNiche, sort, setSort }) {
  const { Icon } = window.LAC;
  const { TYPES, NICHES } = window.LACData;
  return (
    <div className="mk-filterbar">
      <div className="mk-search-row">
        <div className="mk-search">
          <Icon name="search" size={18}/>
          <input placeholder="Search skills, packs, niches…" value={query} onChange={e => setQuery(e.target.value)}/>
        </div>
        <select className="mk-select" value={sort} onChange={e => setSort(e.target.value)}>
          <option value="featured">Sort: Featured</option>
          <option value="score">Highest score</option>
          <option value="price-asc">Price: low to high</option>
          <option value="price-desc">Price: high to low</option>
          <option value="title">A–Z</option>
        </select>
      </div>
      <div className="mk-chips">
        <button className={`mk-chip${typeFilter === 'all' ? ' active' : ''}`} onClick={() => setTypeFilter('all')}>All types</button>
        {TYPES.map(t => (
          <button key={t.key} className={`mk-chip${typeFilter === t.key ? ' active' : ''}`} onClick={() => setTypeFilter(t.key)}>{t.label}</button>
        ))}
        <span style={{ width: 1, background: 'var(--border-2)', margin: '0 4px' }}></span>
        <button className={`mk-chip${niche === 'all' ? ' active' : ''}`} onClick={() => setNiche('all')}>All niches</button>
        {NICHES.map(n => (
          <button key={n} className={`mk-chip${niche === n ? ' active' : ''}`} onClick={() => setNiche(n)}>{n}</button>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ onReset }) {
  const { Icon } = window.LAC;
  return (
    <div className="mk-empty">
      <div className="glyph" style={{ color: 'var(--text-3)' }}><Icon name="search" size={64}/></div>
      <h3>No skills match those filters</h3>
      <p>Try a different niche or clear your search — new skills are added regularly.</p>
      <button className="btn btn-secondary mt-4" onClick={onReset}>Clear filters</button>
    </div>
  );
}

function CompareBar({ compareList, products, onClear, onRemove }) {
  const { Icon } = window.LAC;
  if (compareList.length === 0) return null;
  const items = compareList.map(id => products.find(p => p.id === id)).filter(Boolean);
  return (
    <div style={{
      position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 90,
      background: 'rgba(10,14,35,0.95)', backdropFilter: 'blur(16px)', border: '1px solid var(--border-3)',
      borderRadius: 16, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 14,
      boxShadow: '0 20px 50px rgba(0,0,0,0.5)', maxWidth: 'calc(100vw - 32px)', flexWrap: 'wrap',
    }}>
      <span className="fw-600 fs-13" style={{ color: 'var(--text-2)' }}>Compare ({items.length}/3)</span>
      <div className="row gap-2" style={{ flexWrap: 'wrap' }}>
        {items.map(p => (
          <span key={p.id} className="mk-tag" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {p.title.slice(0, 22)}{p.title.length > 22 ? '…' : ''}
            <span style={{ cursor: 'pointer', opacity: 0.6 }} onClick={() => onRemove(p.id)}><Icon name="close" size={12}/></span>
          </span>
        ))}
      </div>
      <button className="btn btn-primary" style={{ padding: '8px 14px' }} disabled={items.length < 2}>Compare</button>
      <button className="btn btn-ghost" style={{ padding: '8px 10px' }} onClick={onClear}>Clear</button>
    </div>
  );
}

const PAGE_SIZE = 9;

function CatalogPage({ navigate, initialQuery = '' }) {
  const { ProductCard } = window.LAC;
  const { PRODUCTS } = window.LACData;
  const [query, setQuery] = useStateCat(initialQuery);
  const [typeFilter, setTypeFilter] = useStateCat('all');
  const [niche, setNiche] = useStateCat('all');
  const [sort, setSort] = useStateCat('featured');
  const [page, setPage] = useStateCat(1);
  const [compareOn, setCompareOn] = useStateCat(false);
  const [compareList, setCompareList] = useStateCat([]);

  const filtered = useMemo(() => {
    let list = PRODUCTS.filter(p => {
      if (typeFilter !== 'all' && p.type !== typeFilter) return false;
      if (niche !== 'all' && !p.niches.includes(niche)) return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        const hay = (p.title + ' ' + p.summary + ' ' + p.niches.join(' ')).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    list = [...list].sort((a, b) => {
      if (sort === 'featured') return (b.featured - a.featured) || (b.score || 0) - (a.score || 0);
      if (sort === 'score') return (b.score || 0) - (a.score || 0);
      if (sort === 'price-asc') return a.price - b.price;
      if (sort === 'price-desc') return b.price - a.price;
      if (sort === 'title') return a.title.localeCompare(b.title);
      return 0;
    });
    return list;
  }, [query, typeFilter, niche, sort]);

  React.useEffect(() => { setPage(1); }, [query, typeFilter, niche, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleCompare = (id) => setCompareList(list =>
    list.includes(id) ? list.filter(x => x !== id) : (list.length < 3 ? [...list, id] : list));

  const reset = () => { setQuery(''); setTypeFilter('all'); setNiche('all'); };

  return (
    <div className="mk-wrap" style={{ paddingTop: 40, paddingBottom: 70 }}>
      <div className="mk-sec-head" style={{ marginBottom: 22 }}>
        <div>
          <div className="mk-sec-title">Skill catalog</div>
          <div className="mk-sec-sub">{filtered.length} verified {filtered.length === 1 ? 'listing' : 'listings'} · skills & content packs</div>
        </div>
        <label className="mk-compare" style={{ fontSize: 13 }}>
          <input type="checkbox" checked={compareOn} onChange={e => { setCompareOn(e.target.checked); if (!e.target.checked) setCompareList([]); }}/>
          Compare mode
        </label>
      </div>

      <FilterBar {...{ query, setQuery, typeFilter, setTypeFilter, niche, setNiche, sort, setSort }}/>

      {pageItems.length === 0 ? (
        <EmptyState onReset={reset}/>
      ) : (
        <div className="mk-grid">
          {pageItems.map(p => (
            <ProductCard key={p.id} product={p} onOpen={() => navigate('/skills/' + p.slug)}
              compareOn={compareOn} compareList={compareList} onToggleCompare={toggleCompare}/>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mk-pagination">
          <button className="mk-page-btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
            <button key={n} className={`mk-page-btn${n === page ? ' active' : ''}`} onClick={() => setPage(n)}>{n}</button>
          ))}
          <button className="mk-page-btn" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>›</button>
        </div>
      )}

      {compareOn && <CompareBar compareList={compareList} products={PRODUCTS} onClear={() => setCompareList([])} onRemove={toggleCompare}/>}
    </div>
  );
}

window.LACCatalog = { CatalogPage };
