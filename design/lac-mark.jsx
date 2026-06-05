// LACMark — Let Agents Cook holographic agent-head logo (v3).
// Right-facing line-art profile built from glowing circuit strokes: signature
// glowing ear-ring, eye, temple node, crown seam + a halo of integrated symbols
// (cog+bolt, chip, brain, node-cluster) that drop away at small sizes.
// Tuned to the violet / cyan-spark palette of the site.
// Exports: window.LACMark, window.LACWordmark

(function () {
  const HEAD  = "M 146 200 L 160 150 C 174 146 174 130 172 124 C 169 114 164 106 161 103 C 156 78 138 56 104 47 C 70 39 44 66 40 100 C 37 130 53 156 67 163 C 76 169 82 178 84 200 Z";
  const JAW   = "M 112 134 Q 130 156 160 150";
  const CROWN = "M 102 50 C 130 54 148 72 152 92";
  const NECK1 = "M 108 176 L 150 176";
  const NECK2 = "M 114 188 L 146 188";

  function sym(kind, cx, cy, s, stroke, lac) {
    if (kind === 'cog') {
      let teeth = '';
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        const x1 = cx + Math.cos(a) * s, y1 = cy + Math.sin(a) * s;
        const x2 = cx + Math.cos(a) * (s + s * 0.42), y2 = cy + Math.sin(a) * (s + s * 0.42);
        teeth += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>`;
      }
      return `<g stroke="${stroke}" fill="none" stroke-width="1.4" stroke-linecap="round">
        <circle cx="${cx}" cy="${cy}" r="${s}"/>${teeth}
        <path d="M ${cx + 1.5} ${cy - s * 0.55} L ${cx - 1.8} ${cy + 0.4} L ${cx + 0.6} ${cy + 0.4} L ${cx - 1.5} ${cy + s * 0.55}" stroke="${lac}" stroke-width="1.5"/>
      </g>`;
    }
    if (kind === 'chip') {
      const pins = [];
      for (let i = -1; i <= 1; i++) {
        pins.push(`<line x1="${cx + i * s * 0.6}" y1="${cy - s - s * 0.5}" x2="${cx + i * s * 0.6}" y2="${cy - s}"/>`);
        pins.push(`<line x1="${cx + i * s * 0.6}" y1="${cy + s}" x2="${cx + i * s * 0.6}" y2="${cy + s + s * 0.5}"/>`);
        pins.push(`<line x1="${cx - s - s * 0.5}" y1="${cy + i * s * 0.6}" x2="${cx - s}" y2="${cy + i * s * 0.6}"/>`);
        pins.push(`<line x1="${cx + s}" y1="${cy + i * s * 0.6}" x2="${cx + s + s * 0.5}" y2="${cy + i * s * 0.6}"/>`);
      }
      return `<g stroke="${stroke}" fill="none" stroke-width="1.4" stroke-linecap="round">
        <rect x="${cx - s}" y="${cy - s}" width="${s * 2}" height="${s * 2}" rx="${s * 0.3}"/>
        ${pins.join('')}<circle cx="${cx}" cy="${cy}" r="${s * 0.34}" fill="${lac}" stroke="none"/>
      </g>`;
    }
    if (kind === 'brain') {
      return `<g stroke="${stroke}" fill="none" stroke-width="1.4" stroke-linecap="round">
        <path d="M ${cx - s} ${cy + s * 0.4} Q ${cx - s * 1.2} ${cy - s} ${cx} ${cy - s} Q ${cx + s * 1.2} ${cy - s} ${cx + s} ${cy + s * 0.4} Q ${cx + s} ${cy + s} ${cx} ${cy + s * 0.9} Q ${cx - s} ${cy + s} ${cx - s} ${cy + s * 0.4} Z"/>
        <path d="M ${cx} ${cy - s} L ${cx} ${cy + s * 0.9} M ${cx - s * 0.5} ${cy - s * 0.4} Q ${cx} ${cy} ${cx - s * 0.3} ${cy + s * 0.4} M ${cx + s * 0.5} ${cy - s * 0.4} Q ${cx} ${cy} ${cx + s * 0.3} ${cy + s * 0.4}"/>
      </g>`;
    }
    if (kind === 'nodes') {
      return `<g stroke="${stroke}" fill="none" stroke-width="1.4">
        <line x1="${cx - s}" y1="${cy - s * 0.6}" x2="${cx + s * 0.4}" y2="${cy + s}"/>
        <line x1="${cx + s}" y1="${cy - s * 0.8}" x2="${cx + s * 0.4}" y2="${cy + s}"/>
        <line x1="${cx - s}" y1="${cy - s * 0.6}" x2="${cx + s}" y2="${cy - s * 0.8}"/>
        <circle cx="${cx - s}" cy="${cy - s * 0.6}" r="2.4" fill="${lac}" stroke="none"/>
        <circle cx="${cx + s}" cy="${cy - s * 0.8}" r="2.4" fill="${lac}" stroke="none"/>
        <circle cx="${cx + s * 0.4}" cy="${cy + s}" r="2.4" fill="${lac}" stroke="none"/>
      </g>`;
    }
    return '';
  }

  function logoSVG(opts = {}) {
    const { size = 130, variant = 'holo', blink = true, forceOrbits = null, uid: uidIn } = opts;
    const uid = uidIn || ('v' + Math.random().toString(36).slice(2, 7));

    const showOrbits = forceOrbits != null ? forceOrbits : size >= 150;
    const showDetail = size >= 56;
    const showSecondary = size >= 40;
    const glowOn = size >= 28;
    const sw = Math.max(1.7, 2.4 * Math.min(1.15, size / 130));

    let stroke, eyeC, ringC, lacC, headFill;
    if (variant === 'holo') {
      stroke = `url(#gs-${uid})`;
      eyeC = `oklch(0.93 0.15 205)`; ringC = `url(#gs-${uid})`; lacC = `oklch(0.9 0.14 205)`;
      headFill = size < 34 ? `oklch(0.60 0.18 296 / 0.92)` : `url(#gf-${uid})`;
    } else {
      const c = ({ cyan:'oklch(0.84 0.13 205)', violet:'oklch(0.70 0.19 296)', gold:'oklch(0.83 0.158 85)', white:'#f0f2ff', black:'#0a0e23' })[variant] || '#f0f2ff';
      stroke = c; eyeC = c; ringC = c; lacC = c;
      headFill = size < 34 ? c : 'transparent';
    }

    const defs = `<defs>
      <linearGradient id="gs-${uid}" x1="0.1" y1="0.1" x2="0.95" y2="0.95">
        <stop offset="0%" stop-color="oklch(0.72 0.19 300)"/>
        <stop offset="52%" stop-color="oklch(0.75 0.16 282)"/>
        <stop offset="100%" stop-color="oklch(0.84 0.13 212)"/>
      </linearGradient>
      <linearGradient id="gf-${uid}" x1="0" y1="0" x2="0.7" y2="1">
        <stop offset="0%" stop-color="oklch(0.55 0.17 290 / 0.20)"/>
        <stop offset="100%" stop-color="oklch(0.62 0.15 250 / 0.05)"/>
      </linearGradient>
      <radialGradient id="ge-${uid}" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stop-color="oklch(0.97 0.12 205)"/>
        <stop offset="60%" stop-color="${variant === 'holo' ? 'oklch(0.82 0.18 218)' : eyeC}"/>
        <stop offset="100%" stop-color="${variant === 'holo' ? 'oklch(0.6 0.18 275)' : eyeC}" stop-opacity="${variant === 'holo' ? 0 : 1}"/>
      </radialGradient>
      ${glowOn ? `<filter id="gl-${uid}" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="${size >= 96 ? 2.2 : size >= 48 ? 1.3 : 0.7}" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>` : ''}
    </defs>`;

    let orbits = '';
    if (showOrbits) {
      const faint = variant === 'holo' ? `oklch(0.8 0.12 250 / 0.5)` : stroke;
      orbits = `<g opacity="0.92">
        <g stroke="${faint}" stroke-width="1" fill="none" stroke-dasharray="2 3" opacity="0.7">
          <path d="M 100 36 L 102 50"/><path d="M 58 50 L 86 64"/><path d="M 158 54 L 150 74"/><path d="M 40 110 L 60 112"/>
        </g>
        <g filter="${glowOn ? `url(#gl-${uid})` : 'none'}">
          ${sym('cog', 100, 24, 9, stroke, lacC)}
          ${sym('chip', 48, 44, 7, stroke, lacC)}
          ${sym('brain', 166, 44, 9, stroke, lacC)}
          ${sym('nodes', 28, 104, 8, stroke, lacC)}
        </g>
      </g>`;
    }

    const detail = showDetail ? `
      <g stroke="${stroke}" fill="none" stroke-width="${sw * 0.7}" stroke-linecap="round" opacity="0.8" filter="${glowOn ? `url(#gl-${uid})` : 'none'}">
        <path d="${CROWN}"/><path d="${JAW}"/>
        <circle cx="128" cy="74" r="3.2"/><path d="M 128 71 L 128 60 M 131 74 L 144 70"/>
        <path d="${NECK1}" opacity="0.55"/><path d="${NECK2}" opacity="0.45"/>
      </g>` : '';

    const brow = showSecondary ? `<path d="M 139 101 Q 148 97 158 102" fill="none" stroke="${stroke}" stroke-width="${sw * 0.8}" stroke-linecap="round" filter="${glowOn ? `url(#gl-${uid})` : 'none'}"/>` : '';

    const ear = `<g filter="${glowOn ? `url(#gl-${uid})` : 'none'}" fill="none">
      <circle cx="107" cy="120" r="17" stroke="${ringC}" stroke-width="${sw * 0.9}"/>
      <circle cx="107" cy="120" r="10.5" stroke="${ringC}" stroke-width="${sw * 0.8}" opacity="0.85"/>
      ${size >= 32 ? `<circle cx="107" cy="120" r="4.6" fill="${eyeC}" stroke="none"/>` : ''}
    </g>`;

    const eye = `
      <g filter="${glowOn ? `url(#gl-${uid})` : 'none'}">
        <ellipse cx="148" cy="110" rx="7.5" ry="4.4" fill="url(#ge-${uid})"/>
        ${size >= 44 ? `<circle cx="149.5" cy="108.8" r="1.5" fill="#fff"/>` : ''}
      </g>
      ${blink ? `<path class="lac-lid" d="M 140 110 Q 148 104 156 110" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round" transform="scaleY(0)" style="transform-origin:148px 110px; transform-box:fill-box;"/>` : ''}`;

    return `<svg viewBox="0 0 200 200" width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg" data-blink="${blink ? 1 : 0}" role="img" aria-label="Let Agents Cook">
      ${defs}${orbits}
      <path d="${HEAD}" fill="${headFill}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round" filter="${glowOn ? `url(#gl-${uid})` : 'none'}"/>
      ${detail}${ear}${brow}${eye}
    </svg>`;
  }

  // React component wrapper
  function LACMark({ size = 34, variant = 'holo', blink = true, forceOrbits = null, style }) {
    const ref = React.useRef(null);
    const uid = React.useId().replace(/:/g, '');
    const html = logoSVG({ size, variant, blink, forceOrbits, uid });

    React.useEffect(() => {
      if (!blink || !ref.current) return;
      const lid = ref.current.querySelector('.lac-lid');
      if (!lid) return;
      let t1, t2, t3;
      function loop() {
        lid.style.transition = 'transform 80ms ease-in';
        lid.setAttribute('transform', 'scaleY(1)');
        t1 = setTimeout(() => {
          lid.style.transition = 'transform 130ms ease-out';
          lid.setAttribute('transform', 'scaleY(0)');
        }, 110);
        t2 = setTimeout(loop, 3600 + Math.random() * 3600);
      }
      t3 = setTimeout(loop, 1400 + Math.random() * 2400);
      return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
    }, [blink, html]);

    return React.createElement('span', {
      ref, style: { display: 'inline-flex', lineHeight: 0, ...style },
      dangerouslySetInnerHTML: { __html: html },
    });
  }

  function LACWordmark({ size = 34, showTagline = true, blink = true, onClick }) {
    // Logo mark temporarily removed — wordmark only (re-add <LACMark/> later).
    return (
      <div className="mk-brand" onClick={onClick}>
        <div>
          <div className="mk-name wordmark-grad">Let Agents Cook</div>
          {showTagline && <div className="mk-sub">Verified Skills</div>}
        </div>
      </div>
    );
  }

  window.LACMark = LACMark;
  window.LACWordmark = LACWordmark;
  window.LAClogoSVG = logoSVG;

  // Favicon (static, no blink)
  try {
    const fav = logoSVG({ size: 64, blink: false, uid: 'fav' });
    const blob = new Blob([fav], { type: 'image/svg+xml' });
    const link = document.querySelector("link[rel='icon']") || document.createElement('link');
    link.rel = 'icon'; link.type = 'image/svg+xml'; link.href = URL.createObjectURL(blob);
    document.head.appendChild(link);
  } catch (e) {}
})();
