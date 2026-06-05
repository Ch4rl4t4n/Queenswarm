// Let Agents Cook — Product detail + sticky PurchasePanel (listed + listing-soon).
// Exports: window.LACDetail
const { useState: useStateDet } = React;

function PurchasePanel({ product, navigate }) {
  const { Icon } = window.LAC;
  const listed = product.status === 'listed';
  return (
    <aside className="mk-purchase">
      <div className="mk-purchase-card">
        <div className="row between" style={{ alignItems: 'flex-start' }}>
          <span className={`mk-type ${product.type}`}>
            <Icon name={product.type === 'skill' ? 'shield' : 'doc'} size={12}/>
            {window.LACData.typeLabel(product.type)}
          </span>
          {product.score != null && <window.LAC.ScorePill score={product.score}/>}
        </div>

        <div style={{ marginTop: 18 }}>
          {listed
            ? <div className="mk-purchase-price">€{product.price.toFixed(2)}<small>one-time</small></div>
            : <div className="mk-purchase-price" style={{ color: 'var(--text-2)', fontSize: 26 }}>€{product.price.toFixed(2)}<small>at launch</small></div>}
        </div>

        <div className="mk-buy-row">
          {listed ? (
            <a className="btn btn-primary btn-block" href={product.gumroad} target="_blank" rel="noopener noreferrer">
              Buy on Gumroad <Icon name="external" size={16}/>
            </a>
          ) : (
            <div className="mk-soon-panel">
              <div className="t">Listing soon</div>
              <div className="d">This skill is in final verification. Get notified the moment it goes live.</div>
            </div>
          )}

          {/* Phase 2 — multi-marketplace placeholders */}
          <button className="btn-coming" disabled><Icon name="external" size={15}/> More marketplaces — coming soon</button>
        </div>

        {!listed && (
          <button className="btn btn-secondary btn-block" style={{ marginTop: -2 }}>Notify me at launch</button>
        )}

        <div className="mk-trust-list">
          <div className="mk-trust-item"><Icon name="flask" size={16}/><span>Simulate-first verified — outcomes checked before listing.</span></div>
          <div className="mk-trust-item"><Icon name="tag" size={16}/><span>One-time purchase. Own it forever, no subscription.</span></div>
          <div className="mk-trust-item"><Icon name="shield" size={16}/><span>Secure checkout handled by Gumroad.</span></div>
        </div>
      </div>

      <p className="text-4 fs-12" style={{ textAlign: 'center', marginTop: 14, lineHeight: 1.5 }}>
        Delivered as a download through an external marketplace. Let Agents Cook is a catalog — there's no account to create here.
      </p>
    </aside>
  );
}

function Gallery({ product }) {
  const { Icon } = window.LAC;
  const [active, setActive] = useStateDet(0);
  const slots = [0, 1, 2];
  const hue = product.type === 'skill' ? '295' : '195';
  return (
    <div className="mk-gallery">
      <div className="mk-gallery-main" style={{
        background: `radial-gradient(ellipse 100% 90% at ${active === 1 ? '70' : active === 2 ? '40' : '30'}% 25%, oklch(0.42 0.18 ${hue} / 0.5), transparent 60%), linear-gradient(160deg, #0d1230, #0a0e23)`,
      }}>
        <svg width="100%" height="100%" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, opacity: 0.4 }}>
          <defs><pattern id="gg" width="26" height="26" patternUnits="userSpaceOnUse"><path d="M26 0H0V26" fill="none" stroke="oklch(0.7 0.1 280 / 0.14)" strokeWidth="1"/></pattern></defs>
          <rect width="320" height="180" fill="url(#gg)"/>
        </svg>
        <div style={{ position: 'relative', textAlign: 'center', color: `oklch(0.85 0.12 ${hue})` }}>
          <Icon name={product.type === 'skill' ? 'hexagon' : 'doc'} size={56}/>
          <div className="text-3 fs-12 mt-3" style={{ fontFamily: 'var(--font-mono)' }}>
            {active === 0 ? 'cover.html preview' : active === 1 ? 'sample output' : 'verification report'}
          </div>
        </div>
      </div>
      <div className="mk-gallery-thumbs">
        {slots.map(i => (
          <div key={i} className={`mk-gthumb${active === i ? ' active' : ''}`} onClick={() => setActive(i)}
               style={{ display: 'grid', placeItems: 'center', color: 'var(--text-3)' }}>
            <Icon name={i === 0 ? 'doc' : i === 1 ? 'spark' : 'shield'} size={16}/>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProductDetail({ slug, navigate }) {
  const { Icon } = window.LAC;
  const product = window.LACData.PRODUCTS.find(p => p.slug === slug);

  React.useEffect(() => { window.scrollTo(0, 0); }, [slug]);

  if (!product) {
    return (
      <div className="mk-wrap mk-empty">
        <h3>Skill not found</h3>
        <p>That listing doesn't exist or has been moved.</p>
        <button className="btn btn-primary mt-4" onClick={() => navigate('/skills')}>Back to catalog</button>
      </div>
    );
  }

  const related = window.LACData.PRODUCTS.filter(p => p.id !== product.id && p.niches.some(n => product.niches.includes(n))).slice(0, 3);

  return (
    <div className="mk-wrap">
      <div className="mk-detail-grid">
        <div>
          <div className="mk-breadcrumb">
            <a onClick={() => navigate('/')}>Home</a><Icon name="arrow" size={13}/>
            <a onClick={() => navigate('/skills')}>Catalog</a><Icon name="arrow" size={13}/>
            <span className="text-2">{window.LACData.typeLabel(product.type)}</span>
          </div>

          <div className="mk-detail-meta">
            <span className={`mk-type ${product.type}`}><Icon name={product.type === 'skill' ? 'shield' : 'doc'} size={12}/>{window.LACData.typeLabel(product.type)}</span>
            {product.featured && <span className="mk-corner featured">Featured</span>}
            {product.status === 'soon' && <span className="mk-soon-label"><span className="d"></span>Listing soon</span>}
            {product.sales != null && <span className="mk-downloads" style={{ fontSize: 13 }}><Icon name="download" size={14}/>{window.LAC.formatCount(product.sales)} downloads</span>}
          </div>

          <h1 className="mk-detail-title">{product.title}</h1>
          <p className="mk-lede" style={{ marginTop: 0, marginBottom: 22 }}>{product.summary}</p>

          <Gallery product={product}/>

          <div className="mk-card-tags" style={{ marginBottom: 8 }}>
            {product.niches.map(n => <span key={n} className="mk-tag" style={{ fontSize: 12, padding: '5px 11px' }}>{n}</span>)}
          </div>

          <div className="mk-prose">
            <h3>Overview</h3>
            <p>{product.description}</p>

            <h3>What you get</h3>
            <ul className="mk-checklist">
              {product.whatYouGet.map(w => (
                <li key={w}><Icon name="check" size={18}/><span>{w}</span></li>
              ))}
            </ul>

            <h3>Verified, not promised</h3>
            <p>
              Before this {product.type === 'skill' ? 'skill' : 'pack'} was listed, it ran through a simulate-first
              verification pass. The quality score{product.score != null ? ` of ${product.score}` : ''} reflects how it
              performed against its brief — measured, not marketed. <a className="gold" style={{ cursor: 'pointer' }} onClick={() => navigate('/verify-first')}>Learn about verify-first →</a>
            </p>
          </div>

          {related.length > 0 && (
            <div style={{ marginTop: 40 }}>
              <div className="mk-sec-title" style={{ fontSize: 20, marginBottom: 16 }}>Related skills</div>
              <div className="mk-grid">
                {related.map(p => <window.LAC.ProductCard key={p.id} product={p} onOpen={() => navigate('/skills/' + p.slug)}/>)}
              </div>
            </div>
          )}
        </div>

        <PurchasePanel product={product} navigate={navigate}/>
      </div>
    </div>
  );
}

window.LACDetail = { ProductDetail };
