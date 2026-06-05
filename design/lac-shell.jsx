// Let Agents Cook — shell + shared components.
// Exports: window.LAC = { Icon, MarketingShell, ProductCard, ScorePill, CoverArt, NAV }
const { useState, useEffect, useRef } = React;

/* ---------- Icons (inline, stroke-based) ---------- */
const ICONS = {
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  check: 'M20 6 9 17l-5-5',
  external: 'M14 3h7v7M21 3l-9 9M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5',
  shield: 'M12 3 5 6v6c0 4 3 6.5 7 8 4-1.5 7-4 7-8V6l-7-3Z',
  doc: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5ZM14 3v5h5M9 13h6M9 17h6',
  checklist: 'M9 6h11M9 12h11M9 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2',
  hexagon: 'M12 2.5 20 7v10l-8 4.5L4 17V7l8-4.5Z',
  spark: 'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18',
  flask: 'M9 3h6M10 3v6L5 19a1.5 1.5 0 0 0 1.4 2h11.2A1.5 1.5 0 0 0 19 19l-5-10V3M7.5 14h9',
  menu: 'M4 7h16M4 12h16M4 17h16',
  close: 'M6 6l12 12M18 6 6 18',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7l1-8Z',
  tag: 'M3 12V5a2 2 0 0 1 2-2h7l9 9-9 9-9-9ZM7.5 7.5h.01',
  star: 'M12 3l2.6 5.6 6 .8-4.4 4.2 1.1 6L12 17l-5.3 2.6 1.1-6L3.4 9.4l6-.8L12 3Z',
  download: 'M12 3v11M8 11l4 4 4-4M5 20h14',
};
function formatCount(n) {
  if (n == null) return '';
  return n >= 1000 ? (n / 1000).toFixed(n % 1000 >= 100 ? 1 : 0).replace('.0', '') + 'k' : String(n);
}
function Icon({ name, size = 18, fill = 'none', style, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={style} className={className}>
      <path d={ICONS[name]}/>
    </svg>
  );
}

/* ---------- Score pill ---------- */
function ScorePill({ score }) {
  if (score == null) return null;
  return <span className="mk-score"><Icon name="spark" size={12}/>Score {score}</span>;
}

/* ---------- Cover art (deterministic gradient + glyph by type/niche) ---------- */
function CoverArt({ product, className = 'mk-card-cover' }) {
  const isSkill = product.type === 'skill';
  const glyph = isSkill ? 'hexagon' : 'doc';
  const hue = isSkill ? '295' : '195';
  const seed = product.id * 47 % 60;
  return (
    <div className={className} style={{
      background: `radial-gradient(ellipse 120% 90% at ${30 + seed}% 20%, oklch(0.42 0.18 ${hue} / 0.55), transparent 60%), radial-gradient(ellipse 90% 80% at 80% 90%, oklch(0.4 0.14 ${isSkill ? '330' : '160'} / 0.4), transparent 55%), linear-gradient(160deg, #0d1230, #0a0e23)`,
    }}>
      <svg width="100%" height="100%" viewBox="0 0 200 132" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, opacity: 0.5 }}>
        <defs>
          <pattern id={`grid-${product.id}`} width="22" height="22" patternUnits="userSpaceOnUse">
            <path d="M22 0H0V22" fill="none" stroke="oklch(0.7 0.1 280 / 0.12)" strokeWidth="1"/>
          </pattern>
        </defs>
        <rect width="200" height="132" fill={`url(#grid-${product.id})`}/>
      </svg>
      <div className="cover-glyph" style={{ position: 'relative', color: `oklch(0.85 0.12 ${hue})` }}>
        <Icon name={glyph} size={46}/>
      </div>
    </div>
  );
}

/* ---------- Product card ---------- */
function ProductCard({ product, onOpen, compareOn, compareList = [], onToggleCompare }) {
  const { LACData } = window;
  const inCompare = compareList.includes(product.id);
  const compareFull = compareList.length >= 3 && !inCompare;
  return (
    <div className={`mk-card${product.featured ? ' featured' : ''}`} onClick={() => onOpen(product)}>
      <div className="mk-card-top">
        <span className={`mk-type ${product.type}`}>
          <Icon name={product.type === 'skill' ? 'shield' : 'doc'} size={12}/>
          {LACData.typeLabel(product.type)}
        </span>
        {product.featured && <span className="mk-corner featured">Featured</span>}
      </div>

      <CoverArt product={product}/>

      <div className="mk-card-title">{product.title}</div>

      <div className="mk-card-tags">
        {product.niches.slice(0, 3).map(n => <span key={n} className="mk-tag">{n}</span>)}
      </div>

      <div style={{ flex: 1 }}></div>

      <div className="mk-card-foot">
        <div className="row gap-3" style={{ alignItems: 'center' }}>
          {product.status === 'listed'
            ? <span className="mk-price">€{product.price.toFixed(2)}</span>
            : <span className="mk-soon-label"><span className="d"></span>Listing soon</span>}
          {product.score != null && <ScorePill score={product.score}/>}
          {product.sales != null && (
            <span className="mk-downloads" title={`${product.sales.toLocaleString()} downloads`}>
              <Icon name="download" size={13}/>{formatCount(product.sales)}
            </span>
          )}
        </div>
        {compareOn && (
          <label className="mk-compare" onClick={e => e.stopPropagation()} title={compareFull ? 'Max 3' : 'Compare'}>
            <input type="checkbox" checked={inCompare} disabled={compareFull}
                   onChange={() => onToggleCompare(product.id)}/>
            Compare
          </label>
        )}
      </div>
    </div>
  );
}

/* ---------- Nav config ---------- */
const NAV = [
  { key: 'home', label: 'Home', route: '/' },
  { key: 'skills', label: 'Catalog', route: '/skills' },
  { key: 'how', label: 'How it works', route: '/how-it-works' },
  { key: 'verify', label: 'Verify-first', route: '/verify-first' },
];

/* ---------- Marketing shell (nav + footer) ---------- */
function MarketingShell({ route, navigate, children }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const active = (r) => route === r || (r === '/skills' && route.startsWith('/skills'));

  useEffect(() => { setMenuOpen(false); }, [route]);

  return (
    <div className="mk-shell">
      <header className="mk-nav">
        <div className="mk-wrap mk-nav-inner">
          <window.LACWordmark size={34} onClick={() => navigate('/')}/>
          <nav className="mk-links">
            {NAV.map(n => (
              <a key={n.key} className={`mk-link${active(n.route) ? ' active' : ''}`} onClick={() => navigate(n.route)}>{n.label}</a>
            ))}
            <a className="mk-link" title="Coming soon">Free eval checklist<span className="soon-dot">soon</span></a>
          </nav>
          <div className="mk-nav-cta">
            <button className="btn btn-primary" onClick={() => navigate('/skills')}>Browse skills</button>
            <button className="mk-burger" onClick={() => setMenuOpen(o => !o)} aria-label="Menu">
              <Icon name={menuOpen ? 'close' : 'menu'} size={20}/>
            </button>
          </div>
        </div>
        <div className={`mk-mobile-menu${menuOpen ? ' open' : ''}`}>
          {NAV.map(n => (
            <a key={n.key} className={`mk-link${active(n.route) ? ' active' : ''}`} onClick={() => navigate(n.route)}>{n.label}</a>
          ))}
          <a className="mk-link" style={{ opacity: 0.6 }}>Free eval checklist<span className="soon-dot">soon</span></a>
          <button className="btn btn-primary btn-block mt-4" onClick={() => navigate('/skills')}>Browse skills</button>
        </div>
      </header>

      <main style={{ flex: 1 }}>{children}</main>

      <Footer navigate={navigate}/>
    </div>
  );
}

/* ---------- Footer ---------- */
function Footer({ navigate }) {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  return (
    <footer className="mk-footer">
      <div className="mk-wrap">
        <div className="mk-news">
          <div>
            <h3>Get notified when new skills drop</h3>
            <p>Occasional emails about verified releases and bundles. No spam, unsubscribe anytime.</p>
          </div>
          <form className="mk-news-form" onSubmit={e => { e.preventDefault(); if (email) setSent(true); }}>
            {sent ? (
              <div className="row gap-2" style={{ color: 'oklch(0.85 0.14 155)', fontWeight: 600, padding: '13px 0' }}>
                <Icon name="check" size={18}/> You're on the list.
              </div>
            ) : (
              <>
                <input type="email" required placeholder="you@email.com" value={email} onChange={e => setEmail(e.target.value)}/>
                <button className="btn btn-gold" type="submit">Notify me</button>
              </>
            )}
          </form>
        </div>

        <div className="mk-foot-grid">
          <div className="mk-foot-col">
            <window.LACWordmark size={30} showTagline={false} blink={false} onClick={() => navigate('/')}/>
            <p className="text-3 fs-13" style={{ marginTop: 14, maxWidth: 280, lineHeight: 1.55 }}>
              A curated marketplace of verified agent skills and content packs. Every listing is simulate-first and quality-scored before it ships.
            </p>
          </div>
          <div className="mk-foot-col">
            <h5>Browse</h5>
            <a onClick={() => navigate('/skills')}>All skills</a>
            <a onClick={() => navigate('/skills')}>Verified skills</a>
            <a onClick={() => navigate('/skills')}>Content packs</a>
            <a onClick={() => navigate('/skills')}>Featured</a>
          </div>
          <div className="mk-foot-col">
            <h5>Learn</h5>
            <a onClick={() => navigate('/how-it-works')}>How it works</a>
            <a onClick={() => navigate('/verify-first')}>Verify-first</a>
            <a style={{ opacity: 0.55 }}>Free eval checklist</a>
            <a style={{ opacity: 0.55 }}>Categories</a>
          </div>
          <div className="mk-foot-col">
            <h5>Marketplaces</h5>
            <a>Gumroad</a>
            <a style={{ opacity: 0.55 }}>More — coming soon</a>
          </div>
        </div>

        <div className="mk-foot-bar">
          <span>© 2026 Let Agents Cook. All skills independently verified.</span>
          <span className="row gap-4">
            <a className="text-4" style={{ cursor: 'pointer' }}>Terms</a>
            <a className="text-4" style={{ cursor: 'pointer' }}>Privacy</a>
          </span>
        </div>
      </div>
    </footer>
  );
}

window.LAC = { Icon, MarketingShell, ProductCard, ScorePill, CoverArt, NAV, formatCount };
