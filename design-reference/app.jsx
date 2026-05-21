/* Queenswarm shell — sidebar + router + tweaks */
const { useState: useStateApp, useEffect: useEffectApp } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "gold",
  "density": "comfortable",
  "honeycombBg": true,
  "glowIntensity": 50
}/*EDITMODE-END*/;

const NAV = [
  { id: "dashboard",    label: "Dashboard",    icon: "dashboard", key: "H" },
  { id: "swarms",       label: "Swarms",       icon: "swarms",    count: 4, key: "S" },
  { id: "agents",       label: "Agents",       icon: "agents",    count: 40, key: "A" },
  { id: "foragers",     label: "Foragers",     icon: "foragers",  count: 12, key: "F" },
  { id: "tasks",        label: "Tasks",        icon: "tasks",     count: 14, key: "T" },
  { id: "knowledge",    label: "Knowledge",    icon: "knowledge", key: "O" },
  { id: "integrations", label: "Integrations", icon: "integrations", key: "M" },
  { id: "ballroom",     label: "Ballroom",     icon: "ballroom",  key: "B" },
];
const NAV_SECONDARY = [
  { id: "costs",       label: "Costs",       icon: "costs" },
  { id: "leaderboard", label: "Leaderboard", icon: "leaderboard" },
  { id: "settings",    label: "Settings",    icon: "settings" },
  { id: "manual",      label: "Manual",      icon: "manual" },
];

const TENANTS = [
  { id: "queenswarm",     name: "Queenswarm",       sub: "Hive Pro · 5 seats" },
  { id: "acme",           name: "Acme Robotics",    sub: "Hive Pro · 12 seats" },
  { id: "honeyworks",     name: "HoneyWorks Labs",  sub: "Free · 1 seat" },
];

const Sidebar = ({ active, setActive, onLogout, mobileOpen, setMobileOpen }) => {
  const [tenantOpen, setTenantOpen] = useStateApp(false);
  const [tenant, setTenant] = useStateApp(TENANTS[0]);
  return (
  <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
    <div className="brand">
      <div className="brand-mark"><QueenLogo size={36}/></div>
      <div className="col">
        <div className="brand-name">Queenswarm</div>
        <div className="brand-sub">Hive Control · v4</div>
      </div>
      <button className="mobile-nav-toggle" onClick={()=>setMobileOpen(!mobileOpen)}>
        <Icon name={mobileOpen ? "x" : "menu"} size={18}/>
      </button>
    </div>

    {/* Tenant switcher */}
    <div style={{ position: "relative" }}>
      <div className="tenant-switch" onClick={()=>setTenantOpen(!tenantOpen)}>
        <div className="tenant-mark">{tenant.name.charAt(0)}</div>
        <div className="tenant-name">
          <div className="t">{tenant.name}</div>
          <div className="s">{tenant.sub}</div>
        </div>
        <Icon name="chevDown" size={14}/>
      </div>
      {tenantOpen && (
        <div style={{ position: "absolute", top: "100%", left: 0, right: 0, zIndex: 30, background: "var(--bg-2)", border: "1px solid var(--line-strong)", borderRadius: 12, padding: 6, marginTop: 4, boxShadow: "0 12px 32px rgba(0,0,0,0.5)" }}>
          {TENANTS.map(t => (
            <div key={t.id} className="tenant-switch" style={{ marginBottom: 0, border: "none", padding: 8 }} onClick={()=>{ setTenant(t); setTenantOpen(false); }}>
              <div className="tenant-mark">{t.name.charAt(0)}</div>
              <div className="tenant-name"><div className="t">{t.name}</div><div className="s">{t.sub}</div></div>
              {t.id===tenant.id && <Icon name="check" size={14} stroke={2.5}/>}
            </div>
          ))}
        </div>
      )}
    </div>

    <nav className="nav">
      {NAV.map(n => (
        <div key={n.id} className={`nav-item ${active===n.id?"active":""}`} onClick={()=>{ setActive(n.id); setMobileOpen(false); }}>
          <span className="nav-icon"><Icon name={n.icon} size={18}/></span>
          <span>{n.label}</span>
          {n.count && <span className="nav-count">{n.count}</span>}
        </div>
      ))}
      <div style={{ height: 1, background: "var(--line)", margin: "10px 0" }}></div>
      {NAV_SECONDARY.map(n => (
        <div key={n.id} className={`nav-item ${active===n.id?"active":""}`} onClick={()=>{ setActive(n.id); setMobileOpen(false); }}>
          <span className="nav-icon"><Icon name={n.icon} size={18}/></span>
          <span>{n.label}</span>
        </div>
      ))}
    </nav>

    <div className="sidebar-footer">
      <div className="sidebar-status">
        <span className="pulse-dot"></span>
        <div className="col" style={{ flex: 1, lineHeight: 1.3 }}>
          <span style={{ color: "var(--ok)", fontWeight: 600 }}>Hive synced</span>
          <span className="muted" style={{ fontSize: 10 }}>4 swarms · 38ms · $0.04/min</span>
        </div>
      </div>
      <div className="shortcuts">
        <span>Shortcuts ·</span>
        {NAV.filter(n=>n.key).map(n=>(<span key={n.id}> <span className="key">Alt+{n.key}</span></span>))}
      </div>
      <button className="logout-btn" onClick={onLogout}>
        <Icon name="logout" size={16}/>
        Log out
      </button>
    </div>
  </aside>
);
};

const TweaksUI = () => {
  const t = useTweaks(TWEAK_DEFAULTS);
  return (
    <TweaksPanel>
      <TweakSection title="Accent">
        <TweakRadio name="accent" value={t.accent} options={[
          { value: "gold", label: "Gold" },
          { value: "purple", label: "Purple" },
          { value: "mixed", label: "Mixed" },
        ]} onChange={v=>t.setTweak("accent", v)}/>
      </TweakSection>
      <TweakSection title="Density">
        <TweakRadio name="density" value={t.density} options={[
          { value: "compact", label: "Compact" },
          { value: "comfortable", label: "Comfy" },
        ]} onChange={v=>t.setTweak("density", v)}/>
      </TweakSection>
      <TweakSection title="Honeycomb backdrop">
        <TweakToggle value={t.honeycombBg} onChange={v=>t.setTweak("honeycombBg", v)}/>
      </TweakSection>
      <TweakSection title="Glow intensity">
        <TweakSlider value={t.glowIntensity} min={0} max={100} onChange={v=>t.setTweak("glowIntensity", v)}/>
      </TweakSection>
    </TweaksPanel>
  );
};

/* Apply tweaks via data attrs / inline overrides */
const useTweakStyles = () => {
  useEffectApp(() => {
    const apply = (vals) => {
      const root = document.documentElement;
      // accent
      if (vals.accent === "purple") {
        root.style.setProperty("--grad-primary", "linear-gradient(135deg, #7E3FBE 0%, #552583 50%, #2F0F4F 100%)");
      } else if (vals.accent === "mixed") {
        root.style.setProperty("--grad-primary", "linear-gradient(135deg, #7E3FBE 0%, #FDB927 100%)");
      } else {
        root.style.setProperty("--grad-primary", "linear-gradient(135deg, #FDB927 0%, #FFD24D 50%, #C98E0A 100%)");
      }
      // density
      if (vals.density === "compact") {
        root.style.setProperty("--s-6", "16px");
        root.style.setProperty("--s-8", "24px");
        root.style.setProperty("--s-10", "28px");
      } else {
        root.style.setProperty("--s-6", "24px");
        root.style.setProperty("--s-8", "32px");
        root.style.setProperty("--s-10", "40px");
      }
      // honeycomb bg
      document.body.style.setProperty("--hex-opacity", vals.honeycombBg ? "0.5" : "0");
      const sheet = document.styleSheets[0];
      // glow intensity
      const g = Math.max(0.05, (vals.glowIntensity || 50) / 100);
      root.style.setProperty("--glow-gold", `0 0 0 1px rgba(253,185,39,${0.35*g+0.05}), 0 10px 40px rgba(253,185,39,${0.18*g+0.05})`);
    };

    const onMsg = (e) => {
      if (e?.data?.type === "__edit_mode_state_loaded") apply(e.data.values || {});
      if (e?.data?.type === "__edit_mode_set_keys") {
        const merged = { ...TWEAK_DEFAULTS, ...(window.__qsTweaks||{}), ...(e.data.edits||{}) };
        window.__qsTweaks = merged;
        apply(merged);
      }
    };
    window.addEventListener("message", onMsg);
    apply({ ...TWEAK_DEFAULTS, ...(window.__qsTweaks || {}) });

    // honeycomb backdrop visibility hook
    const honeyStyle = document.createElement("style");
    honeyStyle.id = "qs-honey-toggle";
    honeyStyle.textContent = `body::after { opacity: var(--hex-opacity, 0.5) !important; }`;
    document.head.appendChild(honeyStyle);

    return () => { window.removeEventListener("message", onMsg); honeyStyle.remove(); };
  }, []);
};

const App = () => {
  const [loggedIn, setLoggedIn] = useStateApp(true);
  const [active, setActive] = useStateApp("dashboard");
  const [mobileOpen, setMobileOpen] = useStateApp(false);

  useTweakStyles();

  // Alt+key shortcuts
  useEffectApp(() => {
    const handler = (e) => {
      if (!e.altKey) return;
      const k = e.key.toUpperCase();
      const target = NAV.find(n => n.key === k);
      if (target) { e.preventDefault(); setActive(target.id); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!loggedIn) return <LoginScreen onLogin={()=>setLoggedIn(true)}/>;

  const screens = {
    dashboard: <DashboardScreen/>,
    swarms: <SwarmsScreen/>,
    agents: <AgentsScreen/>,
    foragers: <ForagersScreen/>,
    tasks: <TasksScreen/>,
    knowledge: <KnowledgeScreen/>,
    integrations: <IntegrationsScreen/>,
    ballroom: <BallroomScreen/>,
    costs: <CostsScreen/>,
    leaderboard: <LeaderboardScreen/>,
    settings: <SettingsScreen/>,
    manual: <ManualScreen/>,
  };

  return (
    <div className="app">
      <Sidebar active={active} setActive={setActive} onLogout={()=>setLoggedIn(false)} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen}/>
      <main className="main" data-screen-label={active}>
        {screens[active]}
      </main>
      {active !== "ballroom" && (
        <button className="fab-ballroom" onClick={()=>setActive("ballroom")}>
          <Icon name="mic" size={18}/>
          Open Ballroom
        </button>
      )}
      <TweaksUI/>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
