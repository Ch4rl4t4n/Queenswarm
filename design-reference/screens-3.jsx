/* Knowledge + Integrations screens */

const KnowledgeScreen = () => {
  const [tab, setTab] = useState("hivemind");
  const [query, setQuery] = useState("");

  const subtabs = [
    { id: "hivemind", label: "HiveMind", icon: "graph" },
    { id: "outputs",  label: "Outputs · Archive", icon: "save" },
    { id: "recipes",  label: "Recipes · Learning", icon: "book" },
    { id: "dreaming", label: "Dreaming", icon: "moon" },
    { id: "memory",   label: "Curated memory", icon: "layers" },
    { id: "goals",    label: "Goals", icon: "flag" },
  ];

  const recallHits = [
    { title: "Onboarding flow A — design memo", score: 0.94, source: "outputs/2026-04-19", tags: ["memo","UX"] },
    { title: "Vendor handshake recipe · Calendly", score: 0.89, source: "recipes/calendly_oauth", tags: ["recipe","oauth"] },
    { title: "Queen routing decisions · 30-day window", score: 0.81, source: "hivemind/queen_log", tags: ["log","cost"] },
    { title: "Customer #842 history dossier", score: 0.78, source: "hivemind/cust_842", tags: ["customer"] },
  ];

  const recipes = [
    { name: "Calendly OAuth handshake", uses: 142, success: "98%", score: 9.4, tags: ["oauth","calendar"] },
    { name: "Stripe invoice reconciliation", uses: 89, success: "94%", score: 9.0, tags: ["billing","reconciliation"] },
    { name: "Onboarding A/B variant ship", uses: 56, success: "91%", score: 8.7, tags: ["UX","experiment"] },
    { name: "Q3 retro 1-pager synthesis", uses: 41, success: "100%", score: 9.6, tags: ["retro","memo"] },
    { name: "Knowledge graph audit + repair", uses: 22, success: "86%", score: 8.4, tags: ["graph","audit"] },
  ];

  const dreams = [
    { date: "May 17 · 03:42", insight: "Onboarding drop-off step-4 verification cluster ↔ low-trust mobile sessions", confidence: 0.91 },
    { date: "May 16 · 03:38", insight: "Recipe 'Calendly handshake' under-used in EU tenants — propose default", confidence: 0.84 },
    { date: "May 15 · 03:40", insight: "Cost spike on Grok during 14:00-16:00 UTC — propose pre-routing to Claude", confidence: 0.88 },
  ];

  const proposals = [
    { id: "p-1", text: "Promote 'verify-step-4' to default in retrieval contract", source: "Sentinel", confidence: 0.92 },
    { id: "p-2", text: "Deprecate recipe 'manual_oauth_v1' — 0 uses in 30d", source: "RecipeKeeper", confidence: 0.99 },
    { id: "p-3", text: "Add edge: customer_history ↔ pricing_objection (frequency 0.41)", source: "Oracle", confidence: 0.83 },
  ];

  return (
    <>
      <PageHeader
        title="Knowledge"
        desc="One plane — HiveMind retrieval, outputs archive, recipes/learning, dreaming cycles, curated memory, goals."
        actions={<>
          <Btn variant="ghost" size="sm" icon="sparkleSm">Retrieval session</Btn>
          <Btn variant="ghost" size="sm" icon="plus">New task</Btn>
          <Btn variant="primary" size="sm" icon="ballroom">Ballroom</Btn>
        </>}
      />

      <div className="subtab-row">
        {subtabs.map(s => (
          <button key={s.id} className={`subtab ${tab===s.id?"active":""}`} onClick={()=>setTab(s.id)}>
            <Icon name={s.icon} size={14}/>{s.label}
          </button>
        ))}
      </div>

      {/* Command center */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div>
            <span className="label-kicker">Knowledge command center</span>
            <h2 style={{ marginTop: 6 }}>Retrieval contract</h2>
            <p className="desc">Unified lane for retrieval-contract context, output archive, recipe / dreaming loops.</p>
          </div>
        </div>

        <div className="search-input" style={{ marginBottom: 16 }}>
          <Icon name="search" size={16}/>
          <input className="input" placeholder="Filter blocks · graph, archive, pollen, recipes…" value={query} onChange={e=>setQuery(e.target.value)}/>
        </div>

        <div className="cols-2">
          <div className="card card-tight" style={{ background: "rgba(126,63,190,0.06)" }}>
            <div className="label-kicker mb-3">Retrieval contract</div>
            <div className="mono" style={{ fontSize: 13, color: "var(--gold)" }}>customer_history + policy + last_3_tasks</div>
            <div className="muted mt-2">Used by Queen for every new mission brief.</div>
          </div>
          <div className="card card-tight" style={{ background: "rgba(253,185,39,0.04)" }}>
            <div className="label-kicker mb-3">Skill pack preset</div>
            <div className="mono" style={{ fontSize: 13, color: "var(--purple-bright)" }}>context + decide + tdd + diagnose</div>
            <div className="muted mt-2">Active across Eval &amp; Action swarms.</div>
          </div>
        </div>
      </div>

      {tab === "hivemind" && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <div>
                <h2>HiveMind · graph + vault + search</h2>
                <p className="desc">Neo4j semantic graph · ChromaDB vector fallback · retrieval-aware prompting.</p>
              </div>
              <div className="row gap-2">
                <Btn variant="ghost" size="sm">Quick ingest · task</Btn>
                <Btn variant="ghost" size="sm">Quick ingest · supervisor</Btn>
              </div>
            </div>

            <div className="row gap-3" style={{ marginBottom: 20 }}>
              <Btn variant="ghost" icon="refresh" size="sm">Refresh graph</Btn>
              <Btn variant="primary" icon="download" size="sm">Export ZIP</Btn>
            </div>

            <div className="row gap-3 wrap" style={{ marginBottom: 20 }}>
              <input className="input flex-1" placeholder="Global semantic probe — hive_mind chroma lane…" defaultValue="how did Queen decide on Grok routing last week?"/>
              <Btn variant="ghost" size="sm" icon="search">Search</Btn>
              <Btn variant="primary" size="sm" icon="sparkleSm">Recall preview</Btn>
            </div>

            <div className="cols-2">
              <div style={{ background: "rgba(7,3,15,0.5)", border: "1px solid var(--line)", borderRadius: 16, padding: 24, position: "relative", overflow: "hidden", minHeight: 320 }}>
                <div className="row-between" style={{ position: "relative", zIndex: 2, marginBottom: 16 }}>
                  <span className="badge badge-gold">128 nodes · 412 ribs</span>
                  <Btn variant="ghost" size="sm" icon="refresh">Re-layout</Btn>
                </div>
                <svg viewBox="0 0 400 240" style={{ width: "100%", height: 240 }}>
                  <defs>
                    <radialGradient id="node-glow"><stop offset="0%" stopColor="#FDB927" stopOpacity="0.4"/><stop offset="100%" stopColor="#FDB927" stopOpacity="0"/></radialGradient>
                  </defs>
                  {[[200,120,80,60],[200,120,320,60],[200,120,80,180],[200,120,320,180],[200,120,140,200],[200,120,260,200],[80,60,140,200],[320,60,260,200],[80,60,60,130],[320,60,340,130]].map((c,i)=>(<line key={i} x1={c[0]} y1={c[1]} x2={c[2]} y2={c[3]} stroke="rgba(126,63,190,0.45)" strokeWidth="1"/>))}
                  <circle cx="200" cy="120" r="32" fill="url(#node-glow)"/>
                  <circle cx="200" cy="120" r="14" fill="#FDB927" stroke="#FFD24D" strokeWidth="2"/>
                  <text x="200" y="124" textAnchor="middle" fontSize="9" fill="#1A0E2E" fontWeight="700" fontFamily="Poppins">Q</text>
                  {[[80,60,"S"],[320,60,"E"],[80,180,"A"],[320,180,"M"],[140,200,"R"],[260,200,"D"],[60,130,"P"],[340,130,"O"]].map((n,i)=>(<g key={i}><circle cx={n[0]} cy={n[1]} r="9" fill="rgba(126,63,190,0.4)" stroke="#7E3FBE" strokeWidth="1.5"/><text x={n[0]} y={n[1]+3} textAnchor="middle" fontSize="8" fill="#F5F1FF" fontWeight="600" fontFamily="Poppins">{n[2]}</text></g>))}
                </svg>
              </div>

              <div className="col gap-3">
                <div className="card card-tight"><div className="row-between"><span className="label-kicker">Embedding hits</span><span className="badge badge-gold">{recallHits.length}</span></div><div className="muted mt-2" style={{ fontSize: 12 }}>Top-k recall · clipped to ballroom budget</div></div>
                {recallHits.map((h,i)=>(
                  <div key={i} className="card card-tight" style={{ padding: 14 }}>
                    <div className="row-between" style={{ marginBottom: 6 }}>
                      <div style={{ fontWeight: 500, fontSize: 13 }}>{h.title}</div>
                      <span className="badge badge-gold">{h.score}</span>
                    </div>
                    <div className="muted mono" style={{ fontSize: 11 }}>{h.source}</div>
                    <div className="row gap-2 mt-2">
                      {h.tags.map(t=><span key={t} className="chip" style={{ fontSize: 10, padding: "3px 8px", pointerEvents: "none" }}>#{t}</span>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div><h3>Memory evolution proposals</h3><p className="desc">Suggested graph edits from reflection cycles — approve to commit, reject to log.</p></div>
              <span className="badge badge-purple">{proposals.length} pending</span>
            </div>
            <div className="col gap-3">
              {proposals.map(p => (
                <div key={p.id} className="row-between wrap" style={{ padding: 12, border: "1px solid var(--line)", borderRadius: 12, gap: 12 }}>
                  <div className="flex-1">
                    <div style={{ fontSize: 14 }}>{p.text}</div>
                    <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>by <span style={{ color: "var(--gold)" }}>{p.source}</span> · confidence {p.confidence}</div>
                  </div>
                  <div className="row gap-2">
                    <Btn variant="ghost" size="sm" icon="x">Reject</Btn>
                    <Btn variant="primary" size="sm" icon="check">Approve</Btn>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {tab === "outputs" && (
        <div className="card">
          <div className="card-header">
            <div><h2>Outputs &amp; archive</h2><p className="desc">Semantic archive search · regenerate · PDF / markdown export in one operator loop.</p></div>
            <div className="row gap-2">
              <Btn variant="ghost" size="sm" icon="download">Export all</Btn>
              <Btn variant="primary" size="sm" icon="sparkleSm">Run dreaming pass</Btn>
            </div>
          </div>
          <div className="cols-3">
            {[
              { title: "Onboarding memo · v3", who: "Scribe", score: "9.4" },
              { title: "Calendly OAuth runbook",who: "Forge", score: "9.0" },
              { title: "Cost routing memo · 30d",who: "Sentinel",score: "8.9" },
              { title: "Q3 retro · 1-pager",   who: "Scribe", score: "9.6" },
              { title: "Pricing teardown",     who: "Oracle", score: "8.7" },
              { title: "Pollen distribution map",who: "RecipeKeeper",score: "8.4" },
            ].map((o,i)=>(
              <div key={i} className="card card-tight">
                <span className="badge badge-purple">output</span>
                <h3 className="mt-3" style={{ fontSize: 14 }}>{o.title}</h3>
                <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>by {o.who} · scored {o.score}/10</p>
                <div className="row gap-2 mt-4">
                  <Btn variant="ghost" size="sm" icon="eye">Open</Btn>
                  <Btn variant="ghost" size="sm" icon="refresh">Regenerate</Btn>
                  <Btn variant="ghost" size="sm" icon="download">PDF</Btn>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "recipes" && (
        <>
          <div className="cols-2 mb-6">
            <Stat label="Recipes saved" value="142" icon="book" iconClass="purple" foot="auto-saved · cosine ≥ 0.85"/>
            <Stat label="Avg success rate" value="92.4%" icon="check" iconClass="green" trend={{ dir:"up", text:"+3% 7d" }}/>
          </div>
          <div className="card">
            <div className="card-header">
              <div><h2>Recipe library</h2><p className="desc">Auto-saved on verified workflows · semantic search (Chroma + pgvector).</p></div>
              <Btn variant="primary" size="sm" icon="plus">New recipe</Btn>
            </div>
            <div className="search-input mb-5">
              <Icon name="search" size={16}/>
              <input className="input" placeholder="Search recipes by name, tag, or semantic query…"/>
            </div>
            <table className="table">
              <thead><tr><th>Recipe</th><th>Tags</th><th>Uses</th><th>Success</th><th>Score</th><th></th></tr></thead>
              <tbody>
                {recipes.map((r,i)=>(
                  <tr key={i}>
                    <td className="task-name">{r.name}</td>
                    <td><div className="row gap-2">{r.tags.map(t=><span key={t} className="badge badge-purple">{t}</span>)}</div></td>
                    <td>{r.uses}</td>
                    <td><span className="badge badge-ok">{r.success}</span></td>
                    <td><span className="pollen-pill"><Icon name="star" size={11}/>{r.score}</span></td>
                    <td><Btn variant="ghost" size="sm" icon="play">Run</Btn></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card mt-6">
            <div className="card-header">
              <div><h3>Learning console</h3><p className="desc">LearningLog reflections per agent-task cycle. Pollen rewards via Maynard-Cross + performance blend.</p></div>
              <Btn variant="ghost" size="sm" icon="play">Run reflection pass</Btn>
            </div>
            <div className="col gap-3">
              {[
                { who: "Sentinel", at: "12m ago", text: "Improved Eval score by 0.4 after switching to recipe 'pricing_objection_v2'.", reward: 24 },
                { who: "Forge",    at: "44m ago", text: "Recipe 'calendly_handshake' triggered fallback to manual_v1 — recipe library updated.", reward: 18 },
                { who: "Scribe",   at: "1h ago",  text: "Summary length tightened by 18% with same retrieval; pollen +12 from imitation.", reward: 12 },
              ].map((r,i)=>(
                <div key={i} className="row gap-3" style={{ padding: 12, border: "1px solid var(--line)", borderRadius: 12, alignItems: "flex-start" }}>
                  <span style={{ color: "var(--gold)", fontWeight: 600, minWidth: 110 }}>{r.who}</span>
                  <div className="flex-1">
                    <div style={{ fontSize: 14 }}>{r.text}</div>
                    <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{r.at}</div>
                  </div>
                  <span className="pollen-pill"><Icon name="pollen" size={11}/>+{r.reward}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {tab === "dreaming" && (
        <div className="card-section">
          <div className="card">
            <div className="card-header">
              <div><h2>Dreaming · nightly memory cycles</h2><p className="desc">Celery beat runs offline insight extraction · upserted to Neo4j and surfaced here.</p></div>
              <div className="row gap-2">
                <Btn variant="ghost" size="sm" icon="play">Run now</Btn>
                <Btn variant="ghost" size="sm">Schedule</Btn>
              </div>
            </div>
            <div className="col gap-3">
              {dreams.map((d,i)=>(
                <div key={i} className="card card-tight" style={{ background: "linear-gradient(135deg, rgba(126,63,190,0.10), rgba(7,3,15,0.5))" }}>
                  <div className="row gap-3" style={{ alignItems: "flex-start" }}>
                    <Icon name="moon" size={22} style={{ color: "var(--purple-bright)" }}/>
                    <div className="flex-1">
                      <div className="row-between">
                        <span className="label-kicker">{d.date}</span>
                        <span className="badge badge-purple">conf {d.confidence}</span>
                      </div>
                      <div className="mt-2" style={{ fontSize: 14 }}>{d.insight}</div>
                      <div className="row gap-2 mt-3">
                        <Btn variant="ghost" size="sm" icon="check">Commit to graph</Btn>
                        <Btn variant="ghost" size="sm" icon="x">Dismiss</Btn>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "memory" && (
        <div className="card">
          <div className="card-header">
            <div><h2>Curated memory</h2><p className="desc">4 tenant-scoped files — manually curated context that always ships with retrieval.</p></div>
            <Btn variant="primary" size="sm" icon="plus">Add file</Btn>
          </div>
          <div className="cols-2">
            {[
              { name: "company_facts.md", size: "12 KB", updated: "Apr 18" },
              { name: "voice_persona.md", size: "4 KB",  updated: "Apr 02" },
              { name: "pricing_principles.md", size: "8 KB", updated: "Mar 21" },
              { name: "design_principles.md", size: "6 KB", updated: "Mar 14" },
            ].map(f => (
              <div key={f.name} className="card card-tight">
                <div className="row-between">
                  <div className="row gap-3">
                    <Icon name="book" size={20}/>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{f.name}</div>
                      <div className="muted" style={{ fontSize: 11 }}>{f.size} · last edit {f.updated}</div>
                    </div>
                  </div>
                  <div className="row gap-2"><Btn variant="ghost" size="sm" icon="edit"/><Btn variant="ghost" size="sm" icon="trash"/></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "goals" && (
        <div className="card">
          <div className="card-header">
            <div><h2>Goals</h2><p className="desc">Long-running goals · Celery-backed execution · SSE stream to Ballroom.</p></div>
            <Btn variant="primary" size="sm" icon="plus">New goal</Btn>
          </div>
          <div className="col gap-3">
            {[
              { name: "Reach 100 paying tenants by Q4", progress: 62, status: "running", eta: "Q3 wk 8", ms: 4 },
              { name: "Reduce onboarding drop-off to < 18%", progress: 41, status: "running", eta: "Aug 14", ms: 3 },
              { name: "Compress LLM cost to $0.50/task", progress: 78, status: "running", eta: "Jul 02", ms: 5 },
              { name: "Establish 6 vendor presets", progress: 100, status: "done", eta: "✓", ms: 6 },
            ].map((g,i)=>(
              <div key={i} className="card card-tight">
                <div className="row-between wrap" style={{ marginBottom: 8 }}>
                  <div className="row gap-3">
                    <span className={`badge ${g.status==="done"?"badge-ok":"badge-info"}`}>{g.status}</span>
                    <div style={{ fontWeight: 500 }}>{g.name}</div>
                  </div>
                  <div className="row gap-3">
                    <span className="muted" style={{ fontSize: 12 }}>{g.ms} milestones · ETA {g.eta}</span>
                    <Btn variant="ghost" size="sm" icon="stop">Halt</Btn>
                    <Btn variant="ghost" size="sm" icon="eye">Stream</Btn>
                  </div>
                </div>
                <div className="bar-track" style={{ height: 6 }}><div className="bar-fill" style={{ width: `${g.progress}%` }}></div></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};

/* ---------- INTEGRATIONS ---------- */
const IntegrationsScreen = () => {
  const [hub, setHub] = useState("active");

  const subtabs = [
    { id: "active",      label: "Active",       icon: "check" },
    { id: "hub",         label: "Connector hub",icon: "integrations" },
    { id: "marketplace", label: "Tools marketplace", icon: "globe" },
    { id: "external",    label: "External projects", icon: "layers" },
    { id: "plugins",     label: "Plugins",      icon: "flask" },
  ];

  const actives = [
    { name: "Auto Workflow Breaker", meta: "vbundled · active", state: "connected", icon: "bolt" },
    { name: "Sub-swarm LangGraph runner", meta: "vbundled · active", state: "connected", icon: "graph" },
    { name: "Docker simulation ledger", meta: "vbundled · active", state: "connected", icon: "cpu" },
    { name: "LiteLLM cost governor", meta: "vbundled · active", state: "connected", icon: "coin" },
    { name: "Browser Operator", meta: "vbundled · active", state: "connected", icon: "globe" },
    { name: "Example tool", meta: "v1.0.0 · inactive", state: "error", icon: "alert" },
  ];

  const vendors = [
    { name: "Gmail · Google Workspace", slug: "gmail_workspace", auth: "oauth2", tools: 8, color: "#EA4335" },
    { name: "Outlook · Microsoft 365",  slug: "outlook_microsoft365", auth: "oauth2", tools: 7, color: "#0078D4" },
    { name: "Google Calendar",          slug: "google_calendar", auth: "oauth2", tools: 6, color: "#4285F4" },
    { name: "GitHub REST",              slug: "github_rest", auth: "oauth2", tools: 12, color: "#F5F1FF" },
    { name: "GitLab REST",              slug: "gitlab_rest", auth: "oauth2", tools: 9, color: "#FC6D26" },
    { name: "Slack Workspace",          slug: "slack_workspace", auth: "oauth2", tools: 11, color: "#4A154B" },
    { name: "Telegram Bot API",         slug: "telegram_bot", auth: "bearer", tools: 6, color: "#26A5E4" },
    { name: "Discord Bot",              slug: "discord_bot", auth: "bearer", tools: 7, color: "#5865F2" },
    { name: "Notion API",               slug: "notion", auth: "bearer", tools: 7, color: "#F5F1FF" },
    { name: "Stripe Billing",           slug: "stripe_billing", auth: "bearer", tools: 8, color: "#635BFF" },
  ];

  const tools = [
    { name: "stripe.create_invoice", category: "billing", uses: 412, latency: "98ms", success: "99.4%", trend: "+8%" },
    { name: "calendar.find_slot",    category: "calendar", uses: 1842, latency: "112ms", success: "98.7%", trend: "+12%" },
    { name: "gmail.send",            category: "email",    uses: 562, latency: "188ms", success: "99.1%", trend: "+3%" },
    { name: "github.open_pr",        category: "code",     uses: 88,  latency: "412ms", success: "94.2%", trend: "-2%" },
    { name: "browser.scrape",        category: "browser",  uses: 1240,latency: "1.2s",  success: "92.1%", trend: "+18%" },
    { name: "notion.create_page",    category: "docs",     uses: 280, latency: "240ms", success: "97.8%", trend: "+4%" },
  ];

  return (
    <>
      <PageHeader
        title="Integrations"
        desc="Connectors · MCP hub · tools marketplace · external projects · plugin lattice."
        actions={<>
          <Btn variant="ghost" size="sm" icon="refresh">Refresh pulse</Btn>
          <Btn variant="primary" size="sm" icon="plus">Add connector</Btn>
        </>}
      />

      <div className="subtab-row">
        {subtabs.map(s => (
          <button key={s.id} className={`subtab ${hub===s.id?"active":""}`} onClick={()=>setHub(s.id)}>
            <Icon name={s.icon} size={14}/>{s.label}
          </button>
        ))}
      </div>

      {hub === "active" && (
        <div className="card">
          <div className="card-header">
            <div><h2>Active integrations</h2><p className="desc">Unified health snapshot across hub, bridges, and plugins.</p></div>
            <span className="badge badge-ok">{actives.filter(a=>a.state==="connected").length}/{actives.length} healthy</span>
          </div>
          <div className="cols-3">
            {actives.map(a => (
              <div key={a.name} className="int-card">
                <div className="int-head">
                  <div className="row gap-3">
                    <div className="int-logo"><Icon name={a.icon} size={18}/></div>
                    <div>
                      <div className="int-name">{a.name}</div>
                      <div className="int-meta">{a.meta}</div>
                    </div>
                  </div>
                  <span className={`badge ${a.state==="connected"?"badge-ok":"badge-err"}`}>{a.state}</span>
                </div>
                <div className="int-foot">
                  <Btn variant="ghost" size="sm">Open</Btn>
                  {a.state==="error" && <Btn variant="ghost" size="sm" icon="refresh">Retry</Btn>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hub === "hub" && (
        <div className="card">
          <div className="card-header">
            <div>
              <span className="label-kicker">Phase 3 · MCP Hub</span>
              <h2 className="mt-2">Dynamic connector hub</h2>
              <p className="desc">10 curated MCP manifests — Gmail, Outlook, Calendar, GitHub, GitLab, Slack, Telegram, Discord, Notion, Stripe.</p>
            </div>
            <Btn variant="primary" size="sm" icon="sparkleSm">HiveMind recall</Btn>
          </div>

          <div className="cols-3" style={{ marginBottom: 20 }}>
            <Stat label="Templates rostered" value="6 / 10" icon="grid" foot="4 awaiting consent" iconClass="purple"/>
            <Stat label="Active slugs" value="3" icon="check" foot="oauth verified" iconClass="green"/>
            <div className="stat" style={{ display: "grid", placeItems: "center" }}>
              <Btn variant="primary" icon="refresh">Refresh pulse</Btn>
            </div>
          </div>

          <div className="row gap-2 wrap" style={{ marginBottom: 16 }}>
            {["Email · 2","Calendar · 1","Git & code · 2","Chat · 3","Knowledge · 1","Billing · 1"].map(g => (
              <span key={g} className="chip" style={{ pointerEvents: "none" }}>{g}</span>
            ))}
          </div>

          <div className="cols-2">
            {vendors.slice(0,6).map(v => (
              <div key={v.slug} className="int-card">
                <div className="int-head">
                  <div className="row gap-3">
                    <div className="int-logo" style={{ background: `${v.color}22`, color: v.color }}>{v.name.charAt(0)}</div>
                    <div>
                      <div className="int-name">{v.name}</div>
                      <div className="int-meta mono">{v.slug}</div>
                    </div>
                  </div>
                  <span className="badge badge-warn">not provisioned</span>
                </div>
                <div className="row gap-4" style={{ fontSize: 12, color: "var(--text-3)", marginTop: 8 }}>
                  <span>auth · <span style={{ color: "var(--text)" }}>{v.auth}</span></span>
                  <span>tools · <span style={{ color: "var(--text)" }}>{v.tools}</span></span>
                </div>
                <div className="int-foot">
                  <Btn variant="ghost" size="sm">Power panel</Btn>
                  <Btn variant="ghost" size="sm">Docs</Btn>
                  <Btn variant="primary" size="sm" icon="bolt">Prefill forge</Btn>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hub === "marketplace" && (
        <>
          <div className="cols-3 mb-6">
            <Stat label="Tools installed" value="48" icon="layers" iconClass="purple"/>
            <Stat label="Avg success rate" value="97.2%" icon="check" iconClass="green"/>
            <Stat label="Avg latency" value="186ms" icon="bolt" iconClass="cyan"/>
          </div>
          <div className="card">
            <div className="card-header">
              <div><h2>Tools marketplace</h2><p className="desc">Registry + monitoring — usage, latency, success rate. One-click install routes tools into supervisor toolsets.</p></div>
              <Btn variant="primary" size="sm" icon="plus">Install from hub</Btn>
            </div>
            <div className="search-input mb-5">
              <Icon name="search" size={16}/>
              <input className="input" placeholder="Search tools by name, category, or capability…"/>
            </div>
            <table className="table">
              <thead><tr><th>Tool</th><th>Category</th><th>Uses · 24h</th><th>Latency</th><th>Success</th><th>Trend</th><th></th></tr></thead>
              <tbody>
                {tools.map((t,i)=>(
                  <tr key={i}>
                    <td className="task-name mono">{t.name}</td>
                    <td><span className="badge badge-purple">{t.category}</span></td>
                    <td>{t.uses.toLocaleString()}</td>
                    <td className="mono">{t.latency}</td>
                    <td><span className="badge badge-ok">{t.success}</span></td>
                    <td><span style={{ color: t.trend.startsWith("-")?"var(--err)":"var(--ok)", fontSize: 12, fontWeight: 600 }}>{t.trend}</span></td>
                    <td><Btn variant="ghost" size="sm" icon="eye">Inspect</Btn></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {hub === "external" && (
        <div className="card">
          <div className="card-header">
            <div><h2>External projects</h2><p className="desc">Register MCP-first integrations with scoped <span className="mono" style={{ color: "var(--gold)" }}>qs_ep_</span> keys · REST <span className="mono">/external/{`{slug}`}/run</span>.</p></div>
            <Btn variant="ghost" size="sm" icon="refresh">Refresh registry</Btn>
          </div>
          <div className="cols-2">
            <div className="card card-tight" style={{ background: "rgba(126,63,190,0.06)" }}>
              <h3>Register bridge</h3>
              <p className="muted mb-4">Mint secrets once — external vaulting stays operator-owned.</p>
              <div className="col gap-3">
                <div className="input-group"><label>Slug</label><input className="input" defaultValue="my-trading-bot"/></div>
                <div className="input-group"><label>Display name</label><input className="input" defaultValue="Paper swarm trader"/></div>
                <div className="input-group"><label>Lane template</label>
                  <select className="select"><option>Generic simulate / echo</option><option>Trading paper</option><option>Custom JSON</option></select>
                </div>
                <Btn variant="primary" icon="plus">Create project</Btn>
              </div>
            </div>
            <div className="card card-tight">
              <h3>Registry</h3>
              <p className="muted mb-4">Active bridges owned by this dashboard session.</p>
              <div className="col gap-3">
                {[
                  { slug: "paper-trader", name: "Paper swarm trader", success: "98%", calls: 482 },
                  { slug: "blog-spinner", name: "Blog post chain",    success: "94%", calls: 142 },
                ].map(b => (
                  <div key={b.slug} className="row-between" style={{ padding: 12, border: "1px solid var(--line)", borderRadius: 12 }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{b.name}</div>
                      <div className="muted mono" style={{ fontSize: 11 }}>{b.slug}</div>
                    </div>
                    <div className="col" style={{ alignItems: "flex-end" }}>
                      <span className="badge badge-ok">{b.success}</span>
                      <span className="muted" style={{ fontSize: 11, marginTop: 2 }}>{b.calls} calls</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {hub === "plugins" && (
        <div className="card">
          <div className="card-header">
            <div><h2>Plugin catalog</h2><p className="desc">Built-in modules + operator uploads. Mount path <span className="mono" style={{ color:"var(--gold)" }}>backend/plugins/user</span>.</p></div>
            <Btn variant="primary" size="sm" icon="upload">Upload .py</Btn>
          </div>
          <div className="cols-2">
            {[
              { name: "Auto workflow breaker", desc: "LLM decomposition + recipe library semantic recall.", state: "active" },
              { name: "Sub-swarm LangGraph runner", desc: "Colony-local execution graphs with imitation + waggle relays.", state: "active" },
              { name: "Docker simulation ledger", desc: "Sandbox gate before verified payloads exit the hive.", state: "active" },
              { name: "LiteLLM cost governor", desc: "Daily envelopes + Postgres cost-records attribution.", state: "active" },
              { name: "Example tool", desc: "Example operator plugin — copy and edit in plugins/user.", state: "inactive" },
            ].map(p => (
              <div key={p.name} className="int-card">
                <div className="row-between">
                  <div className="int-name">{p.name}</div>
                  <span className={`badge ${p.state==="active"?"badge-ok":"badge-warn"}`}>{p.state}</span>
                </div>
                <p className="muted">{p.desc}</p>
                <div className="int-foot">
                  <Toggle on={p.state==="active"} onChange={()=>{}}/>
                  <Btn variant="ghost" size="sm" icon="trash">Delete</Btn>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};

Object.assign(window, { KnowledgeScreen, IntegrationsScreen });
