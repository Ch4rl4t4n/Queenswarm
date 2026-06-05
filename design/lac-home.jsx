// Let Agents Cook — Home page (MarketingHero, trust strip, featured, bundle).
// Exports: window.LACHome

function MarketingHero({ navigate }) {
  const { Icon } = window.LAC;
  const { PRODUCTS } = window.LACData;
  const hero = PRODUCTS[2]; // Instagram calendar — highest score, featured, listed
  return (
    <section className="mk-hero">
      <div className="mk-wrap">
        <div className="mk-hero-grid">
          <div className="mk-rise">
            <span className="mk-eyebrow"><Icon name="shield" size={13}/> Verified · Simulate-first</span>
            <h1 className="mk-h1">Verified agent skills,<br/>ready to <span className="wordmark-grad">cook</span>.</h1>
            <p className="mk-lede">
              A curated marketplace of agent skills and content packs — each one simulate-first,
              quality-scored, and delivered through trusted marketplaces. Buy once, own it forever.
            </p>
            <div className="mk-hero-cta">
              <button className="btn btn-gold btn-lg" onClick={() => navigate('/skills')}>
                Browse the catalog <Icon name="arrow" size={17}/>
              </button>
              <button className="btn btn-secondary btn-lg" onClick={() => navigate('/how-it-works')}>How it works</button>
            </div>
            <div className="mk-hero-stats">
              <div className="mk-hero-stat"><div className="n gold">14</div><div className="l">Skills & packs</div></div>
              <div className="mk-hero-stat"><div className="n">100%</div><div className="l">Simulate-first verified</div></div>
              <div className="mk-hero-stat"><div className="n">€9+</div><div className="l">One-time, own forever</div></div>
            </div>
          </div>

          <div className="mk-hero-art mk-rise" style={{ animationDelay: '0.1s' }}>
            <div className="mk-float-card">
              <div className="mk-card-top">
                <span className={`mk-type ${hero.type}`}><Icon name="doc" size={12}/>{window.LACData.typeLabel(hero.type)}</span>
                <span className="mk-corner featured">Featured</span>
              </div>
              <window.LAC.CoverArt product={hero} className="mk-card-cover" />
              <div className="mk-card-title" style={{ fontSize: 17 }}>{hero.title}</div>
              <div className="mk-card-tags">{hero.niches.map(n => <span key={n} className="mk-tag">{n}</span>)}</div>
              <div className="mk-card-foot">
                <div className="row gap-3"><span className="mk-price">€{hero.price.toFixed(2)}</span><window.LAC.ScorePill score={hero.score}/>{hero.sales != null && <span className="mk-downloads"><Icon name="download" size={13}/>{window.LAC.formatCount(hero.sales)}</span>}</div>
                <button className="btn btn-primary" onClick={() => navigate('/skills/' + hero.slug)}>View</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function TrustStrip() {
  const { Icon } = window.LAC;
  const items = [
    { ic: 'flask', h: 'Simulate-first', p: 'Every skill is dry-run-able. See projected outcomes before anything goes live.' },
    { ic: 'spark', h: 'Quality scored', p: 'Each listing carries a transparent quality score from its verification run.' },
    { ic: 'shield', h: 'Guardrails built in', p: 'Skills refuse off-brief or low-quality output instead of shipping it anyway.' },
    { ic: 'tag', h: 'Own it forever', p: 'One-time purchase through trusted marketplaces. No subscriptions, no lock-in.' },
  ];
  return (
    <section className="mk-section" style={{ paddingTop: 24 }}>
      <div className="mk-wrap">
        <div className="mk-trust-strip">
          {items.map((it, i) => (
            <div className="mk-trust-card mk-rise" key={it.h} style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="ic" style={{ color: 'oklch(0.85 0.12 295)' }}><Icon name={it.ic} size={20}/></div>
              <h4>{it.h}</h4>
              <p>{it.p}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturedSection({ navigate }) {
  const { ProductCard, Icon } = window.LAC;
  const featured = window.LACData.PRODUCTS.filter(p => p.featured);
  return (
    <section className="mk-section">
      <div className="mk-wrap">
        <div className="mk-sec-head">
          <div>
            <div className="mk-sec-title">Featured skills</div>
            <div className="mk-sec-sub">Hand-picked, verified, and live now.</div>
          </div>
          <span className="mk-sec-link" onClick={() => navigate('/skills')}>View all <Icon name="arrow" size={15}/></span>
        </div>
        <div className="mk-grid">
          {featured.map(p => <ProductCard key={p.id} product={p} onOpen={() => navigate('/skills/' + p.slug)}/>)}
        </div>
      </div>
    </section>
  );
}

function BundleSection({ navigate }) {
  const { Icon } = window.LAC;
  return (
    <section className="mk-section" style={{ paddingTop: 0 }}>
      <div className="mk-wrap">
        <div className="mk-bundle">
          <span className="mk-bundle-soon">Coming soon</span>
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 28, alignItems: 'center' }} className="bundle-inner">
            <div>
              <span className="mk-eyebrow"><Icon name="bolt" size={13}/> Starter bundle</span>
              <h3 style={{ fontSize: 26, fontWeight: 800, margin: '14px 0 10px', letterSpacing: '-0.01em' }}>
                The Creator Growth Starter
              </h3>
              <p className="text-2" style={{ fontSize: 15, lineHeight: 1.6, maxWidth: 460 }}>
                Three of our highest-scoring skills, bundled for one price. Newsletter loop, SEO pipeline
                and the lead-magnet factory — everything to build an audience that compounds.
              </p>
              <div className="row gap-3 mt-6" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
                <button className="btn btn-coming" style={{ width: 'auto', padding: '12px 18px' }} disabled>
                  <Icon name="bolt" size={15}/> Bundle pricing — coming soon
                </button>
                <span className="text-3 fs-13">Save vs. buying separately</span>
              </div>
            </div>
            <div className="col gap-3 bundle-cards">
              {window.LACData.PRODUCTS.filter(p => [1,2,14].includes(p.id)).map(p => (
                <div key={p.id} className="glass-light" style={{ padding: 14, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ color: 'oklch(0.85 0.12 295)', flexShrink: 0 }}><Icon name={p.type === 'skill' ? 'hexagon' : 'doc'} size={22}/></div>
                  <div style={{ minWidth: 0 }}>
                    <div className="fw-600 fs-13" style={{ lineHeight: 1.3 }}>{p.title}</div>
                    <div className="text-3 fs-12 mt-1">Score {p.score} · €{p.price.toFixed(2)}</div>
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

function HomePage({ navigate }) {
  return (
    <>
      <MarketingHero navigate={navigate}/>
      <TrustStrip/>
      <FeaturedSection navigate={navigate}/>
      <BundleSection navigate={navigate}/>
    </>
  );
}

window.LACHome = { HomePage };
