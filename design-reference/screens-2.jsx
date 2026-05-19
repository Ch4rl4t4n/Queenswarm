/* Agents + Tasks screens */

const AgentsScreen = () => {
  const [tab, setTab] = useState("All · 40");
  const [view, setView] = useState("grid");

  const tabs = ["All · 40","Unassigned · 4","Scout · 8","Eval · 12","Sim · 6","Action · 14"];

  const agents = [
    { name: "Orchestrator", role: "Queen", score: "9.4" },
    { name: "Scribe", role: "Scout", score: "8.7" },
    { name: "Sentinel", role: "Eval", score: "9.1" },
    { name: "Cartographer", role: "Scout", score: "8.4" },
    { name: "Forge", role: "Action", score: "9.0" },
    { name: "Oracle", role: "Sim", score: "8.9" },
    { name: "Beacon", role: "Action", score: "8.2" },
    { name: "Loom", role: "Scout", score: "8.6" },
    { name: "Nectar", role: "Eval", score: "9.0" },
    { name: "Compass", role: "Sim", score: "7.9" },
    { name: "Anvil", role: "Action", score: "8.8" },
    { name: "Pollen", role: "Scout", score: "8.5" },
  ];

  const sessions = [
    { id: "S-7142", goal: "Investigate onboarding drop-off and propose implementation", status: "running", runtime: "4m 12s", agents: 5 },
    { id: "S-7143", goal: "Audit knowledge graph integrity · Phase 3 manifests", status: "needs_input", runtime: "11m", agents: 3 },
    { id: "S-7138", goal: "Spike: vendor preset for Calendly OAuth handshake", status: "approved", runtime: "23m", agents: 2 },
  ];

  return (
    <>
      <PageHeader
        title="Agents"
        desc="Unified control plane for supervisor sessions, active bees, and hierarchy topology"
        actions={<>
          <span className="muted">40 bees · 4 swarms</span>
          <Btn variant="ghost" icon="plus" size="sm">Templates</Btn>
          <Btn variant="primary" icon="plus" size="sm">Spawn agent</Btn>
        </>}
      />

      {/* Bee role types catalog */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div>
            <h2>Bee role types</h2>
            <p className="desc">11 role archetypes. Each bee picks one — clone, extend, or compose for custom workers.</p>
          </div>
          <Btn variant="ghost" size="sm" icon="plus">New template</Btn>
        </div>
        <div className="cols-3">
          {[
            { e: "🐝", n: "GenericBee",      d: "Catch-all when role is undecided.",       c: 4 },
            { e: "🔍", n: "ScraperBee",      d: "Pulls data from foragers and the web.",   c: 6 },
            { e: "🧪", n: "EvaluatorBee",    d: "Scores and ranks outputs.",               c: 5 },
            { e: "🔮", n: "SimulatorBee",    d: "Runs sandboxed cost / behavior sims.",    c: 3 },
            { e: "📜", n: "ReporterBee",     d: "Narrates outcomes into Ballroom.",        c: 3 },
            { e: "💹", n: "TraderBee",       d: "Executes paper or live trading actions.", c: 2 },
            { e: "📢", n: "MarketerBee",     d: "Crafts campaigns and outreach copy.",     c: 2 },
            { e: "📝", n: "BlogWriterBee",   d: "Long-form drafts and article chains.",    c: 2 },
            { e: "📲", n: "SocialPosterBee", d: "Schedules and posts to social channels.", c: 2 },
            { e: "🎓", n: "LearnerBee",      d: "Adapts from reflections, top-K imitation.", c: 4 },
            { e: "📚", n: "RecipeKeeperBee", d: "Curates and serves recipe library.",      c: 1 },
          ].map(r => (
            <div key={r.n} className="bee-role-card">
              <div className="bee-mark">{r.e}</div>
              <div className="flex-1">
                <div className="row-between">
                  <div style={{ fontWeight: 600 }}>{r.n}</div>
                  <span className="muted" style={{ fontSize: 11 }}>×{r.c}</span>
                </div>
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{r.d}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Supervisor sessions */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div>
            <h2>Dynamic supervisor sessions</h2>
            <p className="desc">Spawn sub-agents, track statuses, and interact through shared memory logs.</p>
          </div>
          <div className="row gap-2">
            <Btn variant="ghost" size="sm" icon="cpu">Tool hub</Btn>
            <Btn variant="ghost" size="sm" icon="ballroom">Open Ballroom</Btn>
          </div>
        </div>

        <div className="stat-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          <Stat label="Sessions total" value="14" icon="agents" iconClass="purple"/>
          <Stat label="Running / needs input" value="3 / 1" icon="bolt"/>
          <Stat label="Routines total" value="6" icon="refresh" iconClass="cyan"/>
          <Stat label="Active / due" value="2 / 1" icon="check" iconClass="green"/>
        </div>

        {/* Browser harness */}
        <div className="card card-tight" style={{ marginTop: 20, background: "rgba(126,63,190,0.08)", borderColor: "rgba(126,63,190,0.25)" }}>
          <div className="row-between wrap mt-2" style={{ marginBottom: 12 }}>
            <div>
              <div style={{ fontWeight: 600 }}>Browser harness</div>
              <div className="muted">Live browser sessions for agent web navigation, form fill, and scraping.</div>
            </div>
            <span className="badge badge-info">2 sessions</span>
          </div>
          <div className="row gap-3 wrap">
            <input className="input flex-1" placeholder="https://example.com" defaultValue="https://docs.queenswarm.love"/>
            <Btn variant="primary" icon="plus" size="sm">New browser session</Btn>
          </div>
          <div className="cols-2 mt-4">
            <div>
              <span className="label-kicker">Domain allowlist</span>
              <div className="row gap-2 wrap mt-2">
                {["queenswarm.love","github.com","calendly.com","stripe.com","notion.so","slack.com"].map(d=>(
                  <span key={d} className="filter-pill"><span>{d}</span><button>×</button></span>
                ))}
                <Btn variant="ghost" size="sm" icon="plus">Add</Btn>
              </div>
            </div>
            <div>
              <span className="label-kicker">Guardrails</span>
              <div className="col gap-2 mt-2">
                <div className="row-between" style={{ fontSize: 13 }}><span>Block private network (10/172/192)</span><Toggle on={true} onChange={()=>{}}/></div>
                <div className="row-between" style={{ fontSize: 13 }}><span>Approve critical actions</span><Toggle on={true} onChange={()=>{}}/></div>
                <div className="row-between" style={{ fontSize: 13 }}><span>Snapshot every navigation</span><Toggle on={true} onChange={()=>{}}/></div>
              </div>
            </div>
          </div>
        </div>


        {/* Session goal */}
        <div className="row gap-3 wrap" style={{ marginTop: 16 }}>
          <input className="input flex-1" placeholder="Session goal — e.g. investigate onboarding drop-off…" defaultValue="Investigate onboarding drop-off and propose implementation"/>
          <select className="select" style={{ width: 160 }} defaultValue="in-process">
            <option>in-process</option>
            <option>scheduled</option>
            <option>archived</option>
          </select>
          <Btn variant="primary" size="sm" icon="play">Create session</Btn>
        </div>

        {/* Voice command */}
        <div className="card card-tight" style={{ marginTop: 16, background: "rgba(7,3,15,0.4)" }}>
          <div className="row-between" style={{ marginBottom: 8 }}>
            <span className="label-kicker">Supervisor voice command</span>
            <Btn variant="ghost" size="sm" icon="mic">Voice input</Btn>
          </div>
          <div className="row gap-3" style={{ alignItems: "center" }}>
            <div className="voice-bars"><span></span><span></span><span></span><span></span><span></span></div>
            <span className="muted">Ready for voice input — live transcript will appear here.</span>
          </div>
        </div>

        {/* Sessions list */}
        <div className="row-between wrap mt-5" style={{ marginBottom: 12 }}>
          <input className="input flex-1" placeholder="Filter sessions by goal / status / runtime…"/>
          <select className="select" style={{ width: 160 }}>
            <option>all statuses</option>
            <option>running</option>
            <option>needs input</option>
            <option>done</option>
          </select>
        </div>

        <div className="col gap-3">
          {sessions.map(s => (
            <div key={s.id} className="card card-tight" style={{ padding: 16 }}>
              <div className="row-between wrap gap-3">
                <div className="flex-1">
                  <div className="row gap-2" style={{ marginBottom: 4 }}>
                    <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>{s.id}</span>
                    <span className={`badge ${s.status==="running"?"badge-info":s.status==="needs_input"?"badge-warn":"badge-ok"}`}>{s.status.replace("_"," ")}</span>
                  </div>
                  <div style={{ fontWeight: 500 }}>{s.goal}</div>
                </div>
                <div className="row gap-4">
                  <span className="muted" style={{ fontSize: 12 }}>{s.runtime} · {s.agents} agents</span>
                  <Btn variant="ghost" size="sm">Open</Btn>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Routines */}
        <div className="card card-tight" style={{ marginTop: 16, background: "rgba(7,3,15,0.4)" }}>
          <div className="row-between mt-2" style={{ marginBottom: 12 }}>
            <div>
              <div style={{ fontWeight: 600 }}>Routines</div>
              <div className="muted">Recurring supervisor sessions via Celery schedule tick.</div>
            </div>
            <span className="badge badge-gold">6 active</span>
          </div>
          <div className="row gap-3 wrap">
            <input className="input flex-1" placeholder="Routine name" defaultValue="Daily knowledge digest"/>
            <input className="input flex-1" placeholder="Goal template" defaultValue="Summarize new outputs · push to #pollen"/>
            <input className="input" style={{ width: 100 }} defaultValue="3600"/>
            <Btn variant="primary" size="sm" icon="plus">Create</Btn>
          </div>
        </div>
      </div>

      {/* Active agents */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div>
            <h2>Active agents</h2>
            <p className="desc">Live roster, health/status, and direct actions for each bee in one scanable board.</p>
          </div>
          <div className="row gap-2">
            <Btn variant="ghost" size="sm" icon="plus">Add agent</Btn>
            <Btn variant="primary" size="sm" icon="play">Balance hive</Btn>
          </div>
        </div>

        <div className="row-between wrap" style={{ marginBottom: 20 }}>
          <div className="tabs">
            {tabs.map(t => (
              <button key={t} className={`chip ${tab===t?"active":""}`} onClick={()=>setTab(t)}>{t}</button>
            ))}
          </div>
          <div className="row gap-2">
            <button className={`chip ${view==="grid"?"active":""}`} onClick={()=>setView("grid")}><Icon name="grid" size={14}/>Grid</button>
            <button className={`chip ${view==="list"?"active":""}`} onClick={()=>setView("list")}><Icon name="list" size={14}/>List</button>
          </div>
        </div>

        <div className="agent-grid">
          {agents.map(a => <HexAgent key={a.name} {...a}/>)}
        </div>
      </div>

      {/* Hierarchy graph */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2>Hierarchy graph</h2>
            <p className="desc">Queen → managers → workers topology with grouped swarm lanes.</p>
          </div>
          <Btn variant="ghost" size="sm" icon="refresh">Re-layout</Btn>
        </div>
        <div className="network">
          <svg viewBox="0 0 800 320">
            <defs>
              <linearGradient id="edge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#FDB927" stopOpacity="0.7"/>
                <stop offset="100%" stopColor="#7E3FBE" stopOpacity="0.5"/>
              </linearGradient>
            </defs>
            {/* edges */}
            {[[400,60,160,180],[400,60,320,180],[400,60,480,180],[400,60,640,180]].map((e,i)=>(
              <line key={i} x1={e[0]} y1={e[1]} x2={e[2]} y2={e[3]} stroke="url(#edge-grad)" strokeWidth="2"/>
            ))}
            {[[160,180,100,280],[160,180,200,280],[320,180,280,280],[320,180,360,280],[480,180,440,280],[480,180,520,280],[640,180,600,280],[640,180,700,280]].map((e,i)=>(
              <line key={i} x1={e[0]} y1={e[1]} x2={e[2]} y2={e[3]} stroke="rgba(126,63,190,0.4)" strokeWidth="1.5"/>
            ))}
            {/* nodes */}
            <HexNode cx={400} cy={60} label="Queen" sub="Orchestrator" gold large/>
            {["Scout","Eval","Sim","Action"].map((l,i)=>(
              <HexNode key={l} cx={160 + i*160} cy={180} label={l} sub="Manager"/>
            ))}
            {[100,200,280,360,440,520,600,700].map((x,i)=>(
              <HexNode key={i} cx={x} cy={280} label={`W${i+1}`} small/>
            ))}
          </svg>
        </div>
      </div>
    </>
  );
};

const HexNode = ({ cx, cy, label, sub, gold, large, small }) => {
  const size = large ? 38 : small ? 18 : 30;
  const h = size * 1.15;
  const r = small ? 2 : large ? 4 : 3;
  // Build rounded-corner hex path centered on (cx, cy)
  const pts = [
    [cx, cy - h],
    [cx + size, cy - h/2],
    [cx + size, cy + h/2],
    [cx, cy + h],
    [cx - size, cy + h/2],
    [cx - size, cy - h/2],
  ];
  const unit = (a, b) => { const m = Math.hypot(a, b); return [a/m, b/m]; };
  let d = "";
  for (let i = 0; i < 6; i++) {
    const prev = pts[(i+5)%6], curr = pts[i], next = pts[(i+1)%6];
    const [tpx, tpy] = unit(prev[0] - curr[0], prev[1] - curr[1]);
    const [tnx, tny] = unit(next[0] - curr[0], next[1] - curr[1]);
    const sx = curr[0] + tpx*r, sy = curr[1] + tpy*r;
    const ex = curr[0] + tnx*r, ey = curr[1] + tny*r;
    d += (i === 0 ? "M " : "L ") + sx.toFixed(2) + " " + sy.toFixed(2) + " ";
    d += "Q " + curr[0].toFixed(2) + " " + curr[1].toFixed(2) + " " + ex.toFixed(2) + " " + ey.toFixed(2) + " ";
  }
  d += "Z";
  return (
    <g>
      <path
        d={d}
        fill={gold ? "rgba(7,3,15,0.85)" : "rgba(7,3,15,0.7)"}
        stroke={gold ? "#FDB927" : "#7E3FBE"}
        strokeWidth={small ? 2 : 3}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {!small && <>
        <text x={cx} y={cy} textAnchor="middle" fill="#F5F1FF" fontSize="12" fontWeight="600" fontFamily="Poppins">{label}</text>
        {sub && <text x={cx} y={cy+14} textAnchor="middle" fill="#877BA8" fontSize="9" fontFamily="Poppins" letterSpacing="0.1em">{sub.toUpperCase()}</text>}
      </>}
      {small && <text x={cx} y={cy+3} textAnchor="middle" fill="#C7BEE2" fontSize="9" fontWeight="600" fontFamily="Poppins">{label}</text>}
    </g>
  );
};

/* ---------- TASKS ---------- */
const TasksScreen = () => {
  const [tab, setTab] = useState("All");
  const [density, setDensity] = useState("Cozy");

  const tasks = [
    { id: "T-9421", name: "Onboarding flow A/B test analysis", swarm: "Eval", status: "running", progress: 73, updated: "2m ago" },
    { id: "T-9420", name: "Synthesize Q3 retro into 1-page memo", swarm: "Scout", status: "done", progress: 100, updated: "11m ago" },
    { id: "T-9418", name: "Vendor handshake: Calendly OAuth", swarm: "Action", status: "queued", progress: 0, updated: "27m ago" },
    { id: "T-9415", name: "Cost simulation · Grok→Claude routing", swarm: "Sim", status: "running", progress: 42, updated: "31m ago" },
    { id: "T-9412", name: "Knowledge graph integrity audit", swarm: "Eval", status: "needs input", progress: 56, updated: "1h ago" },
    { id: "T-9408", name: "Generate persona insights from 20 calls", swarm: "Scout", status: "done", progress: 100, updated: "2h ago" },
  ];

  const lanes = [
    { name: "New task", desc: "Compose and dispatch a mission into the hive queue.", icon: "plus" },
    { name: "Workflows", desc: "Visual DAG execution, pause/resume, and run controls.", icon: "graph" },
    { name: "Jobs", desc: "Inspect async execution jobs, retries, and completion state.", icon: "bolt" },
    { name: "Routines", desc: "Manage supervisor routines and schedule-driven task execution.", icon: "refresh" },
    { name: "Simulations", desc: "Verified simulation ledger and compliance snapshots.", icon: "cpu" },
  ];

  return (
    <>
      <PageHeader
        title="Tasks"
        desc="14 active · 7 pending · 23 completed today"
        actions={<>
          <Btn variant="ghost" size="sm" icon="refresh">Sync</Btn>
          <Btn variant="primary" icon="plus">New task</Btn>
        </>}
      />

      <div className="row gap-3 wrap" style={{ marginBottom: 24 }}>
        <div className="search-input flex-1">
          <Icon name="search" size={16}/>
          <input className="input" placeholder="Filter tasks by name, swarm, status…"/>
        </div>
        <div className="row gap-2">
          {["Cozy","Compact"].map(d => (
            <button key={d} className={`chip ${density===d?"active":""}`} onClick={()=>setDensity(d)}>{d}</button>
          ))}
        </div>
      </div>

      {/* Lane shortcuts */}
      <div className="cols-3" style={{ marginBottom: 24 }}>
        {lanes.slice(0,3).map(l => (
          <div key={l.name} className="card card-tight" style={{ cursor: "pointer" }}>
            <div className="row gap-3">
              <div className="stat-icon"><Icon name={l.icon} size={16}/></div>
              <div className="flex-1">
                <div style={{ fontWeight: 600 }}>{l.name}</div>
                <div className="muted">{l.desc}</div>
              </div>
              <Icon name="arrowRight" size={16}/>
            </div>
          </div>
        ))}
      </div>
      <div className="cols-2" style={{ marginBottom: 24 }}>
        {lanes.slice(3).map(l => (
          <div key={l.name} className="card card-tight" style={{ cursor: "pointer" }}>
            <div className="row gap-3">
              <div className="stat-icon"><Icon name={l.icon} size={16}/></div>
              <div className="flex-1">
                <div style={{ fontWeight: 600 }}>{l.name}</div>
                <div className="muted">{l.desc}</div>
              </div>
              <Icon name="arrowRight" size={16}/>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs + Queue */}
      <div className="card">
        <div className="card-header">
          <div className="tabs">
            {["All","Running","Pending","Done"].map(t => (
              <button key={t} className={`chip ${tab===t?"active":""}`} onClick={()=>setTab(t)}>{t}</button>
            ))}
          </div>
          <Btn variant="primary" icon="plus" size="sm">New task</Btn>
        </div>

        <table className="table">
          <thead>
            <tr><th>Task</th><th>Swarm</th><th>Status</th><th>Progress</th><th>Updated</th><th></th></tr>
          </thead>
          <tbody>
            {tasks.map(t => (
              <tr key={t.id}>
                <td>
                  <div className="task-name">{t.name}</div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>{t.id}</div>
                </td>
                <td><span className="badge badge-purple">{t.swarm}</span></td>
                <td><span className={`badge ${t.status==="running"?"badge-info":t.status==="done"?"badge-ok":t.status==="needs input"?"badge-warn":"badge-gold"}`}>{t.status}</span></td>
                <td>
                  <div className="row gap-2" style={{ minWidth: 140 }}>
                    <div className="bar-track" style={{ height: 5, flex: 1 }}>
                      <div className="bar-fill" style={{ width: `${t.progress}%` }}></div>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--text-3)", width: 32, textAlign: "right" }}>{t.progress}%</span>
                  </div>
                </td>
                <td className="muted">{t.updated}</td>
                <td><Btn variant="ghost" size="sm" icon="eye">View</Btn></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="cols-2 mt-6">
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Performance by tier</h3>
              <p className="desc">Share of agents in the hive · API summary</p>
            </div>
          </div>
          <div>
            <BarRow label="Queen" value="100% · 1" pct={100}/>
            <BarRow label="Managers" value="12% · 5" pct={12}/>
            <BarRow label="Workers" value="78% · 31" pct={78}/>
            <BarRow label="Scouts" value="20% · 8" pct={20}/>
            <BarRow label="Unassigned" value="10% · 4" pct={10}/>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <h3>Recent tasks</h3>
              <p className="desc">Latest 6 rows from /api/v1/tasks</p>
            </div>
          </div>
          <div className="col gap-3">
            {tasks.slice(0,4).map(t => (
              <div key={t.id} className="row gap-3" style={{ paddingBottom: 12, borderBottom: "1px solid var(--line)" }}>
                <span className={`badge ${t.status==="done"?"badge-ok":t.status==="running"?"badge-info":"badge-warn"}`}>{t.status}</span>
                <div className="flex-1">
                  <div style={{ fontSize: 14 }}>{t.name}</div>
                  <div className="muted" style={{ fontSize: 11 }}>{t.id} · {t.swarm} · {t.updated}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
};

Object.assign(window, { AgentsScreen, TasksScreen });
