// Let Agents Cook — static pages: HowItWorks, VerifyFirst.
// Exports: window.LACStatic

function HowItWorks({ navigate }) {
  const { Icon } = window.LAC;
  const steps = [
    { n: '01', ic: 'search', h: 'Browse the catalog', p: 'Filter by skill or content pack, niche and quality score. Every listing shows exactly what you get before you decide.' },
    { n: '02', ic: 'shield', h: 'Check the verification', p: 'Each skill carries a transparent quality score from its simulate-first run. No vanity metrics, no fabricated reviews — just how it performed.' },
    { n: '03', ic: 'external', h: 'Buy on a trusted marketplace', p: 'Purchase securely through Gumroad. One-time payment, instant download. We never touch your card or create an account.' },
    { n: '04', ic: 'flask', h: 'Drop it in and simulate', p: 'Skills are simulate-first: dry-run them in your own stack to preview outcomes before anything goes live.' },
    { n: '05', ic: 'spark', h: 'Ship with guardrails', p: 'Built-in guardrails keep output on-brief and on-brand, refusing low-quality results instead of shipping them.' },
    { n: '06', ic: 'tag', h: 'Own it forever', p: 'No subscription, no lock-in. What you buy is yours to use, adapt and reuse across projects.' },
  ];
  return (
    <div className="mk-wrap">
      <div className="mk-static-hero">
        <span className="mk-eyebrow"><Icon name="flask" size={13}/> How it works</span>
        <h1 style={{ marginTop: 16 }}>From catalog to cooking in four clicks.</h1>
        <p>Let Agents Cook is a curated storefront, not an app. You browse verified skills here, then buy and download them through trusted marketplaces — and run them in your own environment.</p>
      </div>

      <section className="mk-section" style={{ paddingTop: 36 }}>
        <div className="mk-steps">
          {steps.map((s, i) => (
            <div className="mk-step mk-rise" key={s.n} style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="mk-step-n">{s.n}</div>
              <h4>{s.h}</h4>
              <p>{s.p}</p>
            </div>
          ))}
        </div>

        <div className="mk-bundle" style={{ marginTop: 40, background: 'linear-gradient(120deg, oklch(0.30 0.12 295 / 0.4), oklch(0.28 0.1 80 / 0.25))' }}>
          <div style={{ maxWidth: 560 }}>
            <h3 style={{ fontSize: 24, fontWeight: 800, marginBottom: 10 }}>Ready to browse?</h3>
            <p className="text-2" style={{ fontSize: 15, lineHeight: 1.6, marginBottom: 20 }}>
              Fourteen skills and packs, each verified before listing. Most are launching soon — the strongest are live now.
            </p>
            <button className="btn btn-gold btn-lg" onClick={() => navigate('/skills')}>Open the catalog <Icon name="arrow" size={17}/></button>
          </div>
        </div>
      </section>
    </div>
  );
}

function VerifyFirst({ navigate }) {
  const { Icon } = window.LAC;
  const principles = [
    { ic: 'flask', h: 'Simulate before you ship', p: 'Every skill can be dry-run in a sandbox. You see projected outcomes and quality before a single message, post or page goes live.' },
    { ic: 'spark', h: 'Scores, not testimonials', p: 'A quality score comes from a measured verification run against the skill\u2019s brief — not from cherry-picked reviews or invented numbers.' },
    { ic: 'shield', h: 'Guardrails that refuse', p: 'A verified skill would rather refuse than ship thin, off-brief or off-brand output. Guardrails are part of the product, not an afterthought.' },
    { ic: 'doc', h: 'Transparent by default', p: 'What you get is listed plainly: the agent definition, the harness, the templates. No mystery boxes, no bait-and-switch.' },
  ];
  return (
    <div className="mk-wrap">
      <div className="mk-static-hero">
        <span className="mk-eyebrow"><Icon name="shield" size={13}/> Verify-first</span>
        <h1 style={{ marginTop: 16 }}>Verified outcomes, not marketing claims.</h1>
        <p>Most agent skills are sold on promises. Ours are sold on evidence. Verify-first means every listing earns its place with a measured run before it reaches you.</p>
      </div>

      <section className="mk-section" style={{ paddingTop: 36 }}>
        <div className="mk-grid-2">
          {principles.map((s, i) => (
            <div className="mk-trust-card mk-rise" key={s.h} style={{ padding: 26, animationDelay: `${i * 0.05}s` }}>
              <div className="ic" style={{ color: 'oklch(0.85 0.12 295)', width: 46, height: 46 }}><Icon name={s.ic} size={22}/></div>
              <h4 style={{ fontSize: 17 }}>{s.h}</h4>
              <p style={{ fontSize: 14 }}>{s.p}</p>
            </div>
          ))}
        </div>

        <div className="glass" style={{ padding: 32, marginTop: 36 }}>
          <div className="mk-sec-title" style={{ fontSize: 22, marginBottom: 18 }}>How a score is earned</div>
          <div className="mk-steps" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            {[
              { n: 'Brief', p: 'The skill is given a representative task with a clear definition of done.' },
              { n: 'Run', p: 'It executes simulate-first in a sandbox, with guardrails active and outputs captured.' },
              { n: 'Grade', p: 'Output is scored against the brief for adherence, quality and usefulness. That number is the score you see.' },
            ].map((s, i) => (
              <div key={s.n}>
                <div className="mk-step-n" style={{ marginBottom: 12 }}>{i + 1}</div>
                <h4 style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>{s.n}</h4>
                <p className="text-3 fs-13" style={{ lineHeight: 1.55 }}>{s.p}</p>
              </div>
            ))}
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: 40 }}>
          <button className="btn btn-gold btn-lg" onClick={() => navigate('/skills')}>Browse verified skills <Icon name="arrow" size={17}/></button>
        </div>
      </section>
    </div>
  );
}

window.LACStatic = { HowItWorks, VerifyFirst };
