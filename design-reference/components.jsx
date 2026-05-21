/* Shared UI atoms — Queenswarm */
const { useState, useEffect, useRef, useMemo } = React;

/* ---------- ICONS ---------- */
const Icon = ({ name, size = 18, stroke = 2 }) => {
  const paths = {
    dashboard: <><rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/></>,
    agents: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></>,
    foragers: <><path d="M12 2v6"/><path d="M12 22v-6"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="M2 12h6"/><path d="M22 12h-6"/><path d="m4.93 19.07 4.24-4.24"/><path d="m14.83 9.17 4.24-4.24"/></>,
    tasks: <><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></>,
    knowledge: <><path d="M12 2a3 3 0 0 0-3 3v1H7a3 3 0 0 0-3 3v0a3 3 0 0 0 0 6v0a3 3 0 0 0 3 3h2v1a3 3 0 0 0 6 0v-1h2a3 3 0 0 0 3-3v0a3 3 0 0 0 0-6v0a3 3 0 0 0-3-3h-2V5a3 3 0 0 0-3-3Z"/></>,
    integrations: <><path d="M9 2v3"/><path d="M15 2v3"/><path d="M9 19v3"/><path d="M15 19v3"/><path d="M2 9h3"/><path d="M2 15h3"/><path d="M19 9h3"/><path d="M19 15h3"/><rect x="5" y="5" width="14" height="14" rx="3"/></>,
    ballroom: <><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
    manual: <><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></>,
    search: <><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></>,
    plus: <><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>,
    play: <><polygon points="6 4 20 12 6 20 6 4"/></>,
    bolt: <><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></>,
    queue: <><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/></>,
    cpu: <><rect x="4" y="4" width="16" height="16" rx="3"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></>,
    pollen: <><circle cx="12" cy="12" r="3"/><circle cx="12" cy="3" r="2"/><circle cx="12" cy="21" r="2"/><circle cx="3" cy="12" r="2"/><circle cx="21" cy="12" r="2"/><circle cx="5.6" cy="5.6" r="1.5"/><circle cx="18.4" cy="18.4" r="1.5"/><circle cx="5.6" cy="18.4" r="1.5"/><circle cx="18.4" cy="5.6" r="1.5"/></>,
    coin: <><circle cx="12" cy="12" r="10"/><path d="M12 6v12"/><path d="M16 9.5a3 3 0 0 0-3-2.5h-2a2.5 2.5 0 0 0 0 5h2a2.5 2.5 0 0 1 0 5h-2a3 3 0 0 1-3-2.5"/></>,
    arrowRight: <><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></>,
    arrowUp: <><polyline points="18 15 12 9 6 15"/></>,
    arrowDown: <><polyline points="6 9 12 15 18 9"/></>,
    mic: <><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></>,
    refresh: <><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/><path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/></>,
    grid: <><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></>,
    list: <><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></>,
    check: <><polyline points="20 6 9 17 4 12"/></>,
    x: <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="18" x2="18" y2="6"/></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></>,
    eye: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>,
    menu: <><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></>,
    sparkle: <><path d="M12 3l1.9 5.9L20 11l-6.1 2.1L12 19l-1.9-5.9L4 11l6.1-2.1L12 3z"/></>,
    info: <><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></>,
    graph: <><circle cx="6" cy="19" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="18" cy="19" r="2"/><line x1="7.5" y1="17.5" x2="10.5" y2="6.5"/><line x1="13.5" y1="6.5" x2="16.5" y2="17.5"/><line x1="8" y1="19" x2="16" y2="19"/></>,
    crown: <><path d="M3 7l4 5 5-8 5 8 4-5v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/></>,
    send: <><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><polyline points="3 7 12 13 21 7"/></>,
    lock: <><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></>,
    eyeOff: <><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></>,
    swarms: <><polygon points="12,2 22,7 22,17 12,22 2,17 2,7"/><line x1="2" y1="7" x2="12" y2="12"/><line x1="22" y1="7" x2="12" y2="12"/><line x1="12" y1="12" x2="12" y2="22"/></>,
    costs: <><path d="M3 17l4-4 4 4 4-8 6 6"/><path d="M21 17V5h-4"/></>,
    leaderboard: <><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.45 1-1 1H7a1 1 0 0 0-1 1v3h12v-3c0-.55-.45-1-1-1h-2a1 1 0 0 1-1-1v-2.34"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></>,
    shield: <><path d="M12 2L3 7v6c0 5 4 9 9 10 5-1 9-5 9-10V7l-9-5z"/></>,
    sparkleSm: <><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></>,
    pause: <><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></>,
    stop: <><rect x="5" y="5" width="14" height="14" rx="2"/></>,
    flame: <><path d="M8 14s-2-3-2-5a6 6 0 0 1 12 0c0 1-1 3-2 4s-1 2-1 3a3 3 0 0 1-6 0c0-1 0-2-1-2z"/></>,
    chart: <><path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-5"/></>,
    trash: <><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></>,
    edit: <><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></>,
    pin: <><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14"/><path d="M9 17v-5a3 3 0 0 1 3-3 3 3 0 0 1 3 3v5"/><path d="M7 7l5-5 5 5"/></>,
    star: <><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></>,
    flag: <><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></>,
    moon: <><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></>,
    activity: <><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></>,
    layers: <><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></>,
    upload: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></>,
    chevDown: <><polyline points="6 9 12 15 18 9"/></>,
    chevRight: <><polyline points="9 6 15 12 9 18"/></>,
    sliders: <><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></>,
    flask: <><path d="M9 2v6L4 19a2 2 0 0 0 1.7 3h12.6A2 2 0 0 0 20 19L15 8V2"/><line x1="9" y1="2" x2="15" y2="2"/><line x1="6" y1="14" x2="18" y2="14"/></>,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>,
    radio: <><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></>,
    globe: <><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></>,
    alert: <><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></>,
    drag: <><circle cx="9" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="18" r="1"/></>,
    save: <><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></>,
    copy: <><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></>,
    keyIcon: <><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></>,
  };
  const path = paths[name];
  if (!path) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
      {path}
    </svg>
  );
};

/* ---------- BEE LOGO ---------- */
const hexPathFromPoints = (vertices, radius) => {
  const u = (a, b) => { const m = Math.hypot(a, b) || 1; return [a/m, b/m]; };
  let d = "";
  const n = vertices.length;
  for (let i = 0; i < n; i++) {
    const prev = vertices[(i + n - 1) % n];
    const curr = vertices[i];
    const next = vertices[(i + 1) % n];
    const [tpx, tpy] = u(prev[0] - curr[0], prev[1] - curr[1]);
    const [tnx, tny] = u(next[0] - curr[0], next[1] - curr[1]);
    const sx = curr[0] + tpx * radius, sy = curr[1] + tpy * radius;
    const ex = curr[0] + tnx * radius, ey = curr[1] + tny * radius;
    d += (i === 0 ? "M " : "L ") + sx.toFixed(2) + " " + sy.toFixed(2) + " ";
    d += "Q " + curr[0].toFixed(2) + " " + curr[1].toFixed(2) + " " + ex.toFixed(2) + " " + ey.toFixed(2) + " ";
  }
  return d + "Z";
};

const QueenLogo = ({ size = 40 }) => {
  const center = hexPathFromPoints([[32,18],[48,27],[48,45],[32,54],[16,45],[16,27]], 1.5);
  const topHex = hexPathFromPoints([[32,2],[44,9],[44,17],[32,12],[20,17],[20,9]], 1);
  const botHex = hexPathFromPoints([[32,62],[44,55],[44,63],[32,70],[20,63],[20,55]], 1);
  return (
    <svg width={size} height={size * 1.15} viewBox="0 0 64 72" fill="none">
      <defs>
        <linearGradient id="hex-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FFD24D"/>
          <stop offset="60%" stopColor="#FDB927"/>
          <stop offset="100%" stopColor="#C98E0A"/>
        </linearGradient>
        <linearGradient id="hex-purple" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7E3FBE"/>
          <stop offset="100%" stopColor="#552583"/>
        </linearGradient>
      </defs>
      <path d={center} fill="url(#hex-grad)" />
      <path d={topHex} fill="url(#hex-purple)" opacity="0.7"/>
      <path d={botHex} fill="url(#hex-purple)" opacity="0.5"/>
      {/* crown on center */}
      <path d="M22 30l4 5 6-10 6 10 4-5v8h-20z" fill="#2F0F4F" opacity="0.85"/>
      <circle cx="22" cy="30" r="2" fill="#FFD24D"/>
      <circle cx="32" cy="25" r="2" fill="#FFD24D"/>
      <circle cx="42" cy="30" r="2" fill="#FFD24D"/>
    </svg>
  );
};

/* ---------- BUTTONS ---------- */
const Btn = ({ children, variant = "primary", size = "md", icon, onClick, type = "button", ...rest }) => {
  const classes = `btn btn-${variant} ${size !== "md" ? `btn-${size}` : ""}`.trim();
  return (
    <button className={classes} onClick={onClick} type={type} {...rest}>
      {icon && <Icon name={icon} size={16} />}
      {children}
    </button>
  );
};

/* ---------- PAGE HEADER ---------- */
const PageHeader = ({ title, desc, actions, status }) => (
  <div className="page-header">
    <div className="page-title">
      <h1>{title}</h1>
      {desc && <p>{desc}</p>}
    </div>
    <div className="page-actions">
      {actions}
      {status && (
        <div className="status-pill">
          <span className="pulse-dot"></span>
          {status}
        </div>
      )}
    </div>
  </div>
);

/* ---------- STAT ---------- */
const Stat = ({ label, value, icon, iconClass = "", trend, foot, valueClass = "" }) => (
  <div className="stat">
    <div className="stat-head">
      <span className="stat-label">{label}</span>
      <span className={`stat-icon ${iconClass}`}><Icon name={icon} size={16}/></span>
    </div>
    <div className={`stat-value ${valueClass}`}>{value}</div>
    {trend && (
      <div className={`stat-trend ${trend.dir === "down" ? "down" : ""}`}>
        <Icon name={trend.dir === "down" ? "arrowDown" : "arrowUp"} size={12}/>
        {trend.text}
      </div>
    )}
    {foot && <div className="stat-foot">{foot}</div>}
  </div>
);

/* ---------- HEX BADGE (rounded thick-border SVG) ---------- */
const roundedHexPath = (w, h, r) => {
  const pts = [
    [w/2, h*0.04],
    [w*0.96, h*0.27],
    [w*0.96, h*0.73],
    [w/2, h*0.96],
    [w*0.04, h*0.73],
    [w*0.04, h*0.27],
  ];
  const unit = (ax, ay, bx, by) => {
    const dx = bx - ax, dy = by - ay;
    const m = Math.hypot(dx, dy);
    return [dx/m, dy/m];
  };
  let d = "";
  for (let i = 0; i < 6; i++) {
    const prev = pts[(i+5)%6], curr = pts[i], next = pts[(i+1)%6];
    const [tpx, tpy] = unit(curr[0], curr[1], prev[0], prev[1]);
    const [tnx, tny] = unit(curr[0], curr[1], next[0], next[1]);
    const sx = curr[0] + tpx*r, sy = curr[1] + tpy*r;
    const ex = curr[0] + tnx*r, ey = curr[1] + tny*r;
    d += (i === 0 ? "M " : "L ") + sx.toFixed(2) + " " + sy.toFixed(2) + " ";
    d += "Q " + curr[0].toFixed(2) + " " + curr[1].toFixed(2) + " " + ex.toFixed(2) + " " + ey.toFixed(2) + " ";
  }
  return d + "Z";
};

const HexBadge = ({
  size = 120, accent = "gold", fill = "#0A0518",
  name, role, score, online = true, content, glow = true,
}) => {
  const w = size;
  const h = size * 1.05;
  const stroke = Math.max(2.5, size * 0.028);
  const radius = Math.max(5, size * 0.065);
  const path = roundedHexPath(w, h, radius);
  const accentColor = accent === "purple" ? "#7E3FBE" : accent === "cyan" ? "#6FD6FF" : "#FDB927";
  return (
    <div style={{ position: "relative", width: w, height: h, display: "inline-block" }}>
      <svg width={w} height={h} style={{ display: "block", filter: glow ? `drop-shadow(0 0 10px ${accentColor}55)` : "none", overflow: "visible" }}>
        <path
          d={path}
          fill={fill}
          stroke={accentColor}
          strokeWidth={stroke}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      {online && (
        <span style={{
          position: "absolute",
          top: stroke + 4, left: "50%", transform: "translateX(-50%)",
          width: 6, height: 6, borderRadius: "50%",
          background: accentColor,
          boxShadow: `0 0 8px ${accentColor}`,
        }}></span>
      )}
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        textAlign: "center", padding: `${size*0.14}px ${size*0.18}px`,
        pointerEvents: "none",
      }}>
        {content ? content : (
          <>
            {name && <div style={{ fontSize: Math.max(11, size*0.105), fontWeight: 600, color: "#F5F1FF", lineHeight: 1.15 }}>{name}</div>}
            {role && <div style={{ fontSize: Math.max(9, size*0.08), color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.12em", marginTop: 4 }}>{role}</div>}
            {score && <div style={{ fontSize: Math.max(10, size*0.085), color: accentColor, marginTop: 6, fontWeight: 500, display: "flex", alignItems: "center", gap: 4 }}>★ {score}</div>}
          </>
        )}
      </div>
    </div>
  );
};

/* Legacy HexAgent — now uses HexBadge */
const HexAgent = ({ name, role, score, online = true, size = 120 }) => (
  <HexBadge size={size} name={name} role={role} score={score} online={online}/>
);

/* ---------- BAR ROW ---------- */
const BarRow = ({ label, value, pct }) => (
  <div className="bar-row">
    <div className="bar-label">{label}</div>
    <div className="bar-track"><div className="bar-fill" style={{ width: `${pct}%` }}></div></div>
    <div className="bar-value">{value}</div>
  </div>
);

/* ---------- TOGGLE ---------- */
const Toggle = ({ on, onChange }) => (
  <div className={`toggle ${on ? "on" : ""}`} onClick={() => onChange(!on)}></div>
);

/* ---------- EXPORT ---------- */
Object.assign(window, {
  Icon, QueenLogo, Btn, PageHeader, Stat, HexAgent, HexBadge, BarRow, Toggle,
});
