/* Login + Dashboard screens */

const LoginScreen = ({ onLogin }) => {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("admin@queenswarm.love");
  const [password, setPassword] = useState("•••••••••••");
  const [showPwd, setShowPwd] = useState(false);
  const [otp, setOtp] = useState(["","","","","",""]);

  const setOtpCell = (i, v) => {
    const next = [...otp]; next[i] = v.slice(-1); setOtp(next);
    if (v && i<5) document.getElementById(`otp-${i+1}`)?.focus();
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <QueenLogo size={68}/>
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 26, marginTop: 8 }}>Queenswarm</h1>
          <p className="muted" style={{ marginTop: 6 }}>{step===1?"The hive is ready — enter your nectar key":"Verify two-factor code from your authenticator"}</p>
        </div>

        <div className="stepper mt-5">
          <span className={`step-dot ${step>=1?(step>1?"done":"active"):""}`}></span>
          <span className={`step-dot ${step>=2?"active":""}`}></span>
        </div>

        {step === 1 && (
          <div style={{ marginTop: 24 }} className="card-section">
            <div className="input-group">
              <label>Email</label>
              <div style={{ position: "relative" }}>
                <input className="input" style={{ paddingLeft: 44 }} value={email} onChange={e=>setEmail(e.target.value)} />
                <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }}>
                  <Icon name="mail" size={16}/>
                </span>
              </div>
            </div>

            <div className="input-group">
              <div className="row-between">
                <label>Password</label>
                <a style={{ color: "var(--gold)", fontSize: 12, fontWeight: 600, textDecoration: "none", cursor: "pointer" }}>Forgot?</a>
              </div>
              <div style={{ position: "relative" }}>
                <input className="input" style={{ paddingLeft: 44, paddingRight: 44 }} type={showPwd ? "text" : "password"} value={password} onChange={e=>setPassword(e.target.value)} />
                <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }}>
                  <Icon name="lock" size={16}/>
                </span>
                <button onClick={()=>setShowPwd(!showPwd)} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "transparent", border: "none", color: "var(--text-3)", cursor: "pointer", padding: 6 }}>
                  <Icon name={showPwd ? "eyeOff" : "eye"} size={16}/>
                </button>
              </div>
            </div>

            <div className="row-between" style={{ fontSize: 12 }}>
              <div className="row gap-2" style={{ color: "var(--ok)" }}>
                <span className="pulse-dot"></span>
                <span style={{ fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>Hive online</span>
              </div>
              <span className="muted">12 nodes synced · 38ms</span>
            </div>

            <Btn variant="primary" size="lg" onClick={()=>setStep(2)}>
              <span style={{ flex: 1, textAlign: "left" }}>Continue · 2FA</span>
              <Icon name="arrowRight" size={16}/>
            </Btn>
            <Btn variant="ghost" size="sm" onClick={onLogin}>Skip 2FA (dev)</Btn>
          </div>
        )}

        {step === 2 && (
          <div style={{ marginTop: 24 }} className="card-section">
            <div className="row gap-2" style={{ justifyContent: "center", color: "var(--gold)" }}>
              <Icon name="shield" size={16}/>
              <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase" }}>TOTP · Authenticator</span>
            </div>
            <div className="otp-row">
              {otp.map((d,i)=>(<input key={i} id={`otp-${i}`} className="otp-cell" value={d} onChange={e=>setOtpCell(i, e.target.value)} maxLength="1"/>))}
            </div>
            <a style={{ display: "block", textAlign: "center", color: "var(--text-3)", fontSize: 12, cursor: "pointer" }}>Use a backup code instead</a>
            <Btn variant="primary" size="lg" onClick={onLogin}>
              <span style={{ flex: 1, textAlign: "left" }}>Enter the hive</span>
              <Icon name="arrowRight" size={16}/>
            </Btn>
            <Btn variant="ghost" size="sm" onClick={()=>setStep(1)}>Back</Btn>
          </div>
        )}

        <p className="muted" style={{ marginTop: 24, fontSize: 11, textAlign: "center" }}>
          By continuing you agree to our <span style={{ color: "var(--gold)" }}>Terms</span> · <span style={{ color: "var(--gold)" }}>Privacy Policy</span>
        </p>
      </div>
    </div>
  );
};

/* ---------- DASHBOARD ---------- */
const DashboardScreen = () => {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [view, setView] = useState("grid");
  const [mission, setMission] = useState("");

  const subSwarms = [
    { id: "scout", name: "Scout Swarm",  icon: "search", bees: 8,  tasks: 24, latency: "120ms" },
    { id: "eval",  name: "Eval Swarm",   icon: "graph",  bees: 12, tasks: 18, latency: "210ms" },
    { id: "sim",   name: "Sim Swarm",    icon: "cpu",    bees: 6,  tasks: 9,  latency: "340ms" },
    { id: "action",name: "Action Swarm", icon: "bolt",   bees: 14, tasks: 41, latency: "98ms" },
  ];

  const agents = [
    { name: "Orchestrator", role: "Queen", score: "9.4" },
    { name: "Scribe", role: "Scout", score: "8.7" },
    { name: "Sentinel", role: "Eval", score: "9.1" },
    { name: "Cartographer", role: "Scout", score: "8.4" },
    { name: "Forge", role: "Action", score: "9.0" },
    { name: "Oracle", role: "Sim", score: "8.9" },
    { name: "Beacon", role: "Action", score: "8.2" },
    { name: "Loom", role: "Scout", score: "8.6" },
  ];

  const waggleEvents = [
    { from: "Scout Swarm", to: "Eval Swarm",   msg: "Vendor catalog drift — verify 3 new manifests", time: "2m" },
    { from: "Eval Swarm",  to: "Action Swarm", msg: "Onboarding flow A passed simulation — proceed to ship", time: "11m" },
    { from: "Sim Swarm",   to: "Queen",        msg: "Cost envelope nearing 80% — request rebalance", time: "27m" },
  ];

  const workflows = [
    { name: "Customer onboarding · v3",  state: "running", progress: 64, eta: "2m 14s", agents: 5 },
    { name: "Knowledge graph rebuild",   state: "running", progress: 23, eta: "12m",    agents: 8 },
    { name: "Incident triage · #ENG-471",state: "queued",  progress: 0,  eta: "—",       agents: 0 },
    { name: "Q3 retro synthesis",        state: "done",    progress: 100,eta: "✓",       agents: 4 },
  ];

  const suggestions = [
    { id: "s1", from: "Sentinel", text: "Promote variant B to 100% — confidence 0.92, cost delta -$0.18/task", impact: "high" },
    { id: "s2", from: "RecipeKeeper", text: "Deprecate 'manual_oauth_v1' — 0 uses in 30 days", impact: "med" },
    { id: "s3", from: "Oracle", text: "Pre-route Grok → Claude during 14-16 UTC — saves ~$42/day", impact: "high" },
  ];

  const participants = [
    { c: "👑", live: true,  who: "Orchestrator" },
    { c: "📜", live: true,  who: "Scribe" },
    { c: "🛡", live: true,  who: "Sentinel" },
    { c: "🔮", live: false, who: "Oracle" },
    { c: "⚒",  live: true,  who: "Forge" },
  ];

  return (
    <>
      <PageHeader
        title="Queen Dashboard"
        desc="40 agents in the network · 4 swarm nodes · hive sync every 5 min"
        status="Hive open"
        actions={<>
          <Btn variant="ghost" icon="ballroom">Ballroom</Btn>
          <Btn variant="primary" icon="plus">New task</Btn>
        </>}
      />

      <div className="search-input" style={{ marginBottom: 24 }}>
        <Icon name="search" size={16}/>
        <input className="input" placeholder="Search agents, tier, name, swarm…" value={search} onChange={e=>setSearch(e.target.value)} />
      </div>

      <div className="stat-grid">
        <Stat label="Total agents" value="40" icon="agents" iconClass="purple" foot="36 active · 4 idle" trend={{ dir: "up", text: "+3 this week" }}/>
        <Stat label="Running tasks" value="12" icon="bolt" foot="From system pulse" trend={{ dir: "up", text: "+18% vs avg" }}/>
        <Stat label="Queued tasks" value="7" icon="queue" iconClass="cyan" foot="Pending lane"/>
        <Stat label="LLM routing" valueClass="text" value={<><span className="pulse-dot"></span>Routed</>} icon="cpu" iconClass="green" foot="Grok · Claude · GPT"/>
      </div>

      <div className="cols-2" style={{ marginBottom: 24 }}>
        <div className="stat">
          <div className="stat-head">
            <span className="stat-label">Pollen · Roster activity</span>
            <span className="stat-icon"><Icon name="pollen" size={16}/></span>
          </div>
          <div className="stat-value">1,284</div>
          <div className="stat-foot">Signals routed today · last sync 38s ago</div>
          <div style={{ marginTop: 16, display: "flex", alignItems: "end", gap: 4, height: 48 }}>
            {[40,55,32,68,90,72,85,60,78,95,82,70].map((h,i)=>(
              <div key={i} style={{
                flex: 1, height: `${h}%`,
                background: "var(--grad-mix)",
                borderRadius: 3,
                opacity: 0.6 + (i/24)
              }}/>
            ))}
          </div>
        </div>

        <div className="stat">
          <div className="stat-head">
            <span className="stat-label">Costs · 30 days</span>
            <span className="stat-icon"><Icon name="coin" size={16}/></span>
          </div>
          <div className="stat-value">$2,418</div>
          <div className="stat-trend"><Icon name="arrowDown" size={12}/>-12% vs last 30d</div>
          <div className="stat-foot">Sums routed LLM spend — tasks, Ballroom chat, workflows</div>
        </div>
      </div>

      {/* Participants preview */}
      <div className="card card-tight" style={{ marginBottom: 24 }}>
        <div className="row-between wrap" style={{ gap: 12 }}>
          <div className="row gap-4" style={{ alignItems: "center" }}>
            <span className="label-kicker">Ballroom · live participants</span>
            <div className="participants">
              {participants.map((p,i)=>(
                <div key={i} className="participant" title={p.who}>
                  {p.c}{p.live && <span className="live"></span>}
                </div>
              ))}
            </div>
            <span className="muted" style={{ fontSize: 12 }}>{participants.filter(p=>p.live).length}/{participants.length} live · session 04:12</span>
          </div>
          <div className="row gap-2">
            <span className="badge badge-ok">LIVE</span>
            <Btn variant="ghost" size="sm" icon="ballroom">Open Ballroom</Btn>
          </div>
        </div>
      </div>

      {/* Agents card */}
      <div className="card" style={{ marginBottom: 32 }}>
        <div className="card-header">
          <div>
            <h2>Agents</h2>
            <p className="desc">40 bees · 36 assigned · 4 unassigned · 4 swarms · 6 role types</p>
          </div>
          <div className="row gap-2">
            <Btn variant="ghost" icon="plus" size="sm">Add agent</Btn>
            <Btn variant="primary" icon="play" size="sm">Balance hive</Btn>
          </div>
        </div>

        <div className="row-between wrap" style={{ marginBottom: 24 }}>
          <div className="tabs">
            {["All · 40","Unassigned · 4","Scout · 8","Eval · 12","Sim · 6","Action · 14"].map(t => (
              <button key={t} className={`chip ${filter===t.split(" ·")[0]?"active":""}`} onClick={()=>setFilter(t.split(" ·")[0])}>
                {t}
              </button>
            ))}
          </div>
          <div className="row gap-2">
            <button className={`chip ${view==="grid"?"active":""}`} onClick={()=>setView("grid")}><Icon name="grid" size={14}/>Grid</button>
            <button className={`chip ${view==="list"?"active":""}`} onClick={()=>setView("list")}><Icon name="list" size={14}/>List</button>
          </div>
        </div>

        <div className="agent-grid">
          {agents.map(a => <HexAgent key={a.name} {...a} />)}
        </div>
      </div>

      {/* Sub-swarms */}
      <div className="section-title">
        <div>
          <h2>Sub-swarms</h2>
          <div className="desc">Four decentralized swarms with local memory. Global sync every 5 min.</div>
        </div>
        <Btn variant="ghost" icon="refresh" size="sm">Resync</Btn>
      </div>
      <div className="swarm-grid" style={{ marginBottom: 32 }}>
        {subSwarms.map(s => (
          <div key={s.id} className="swarm-card">
            <div className="swarm-head">
              <div className="swarm-name">
                <div className="swarm-icon"><Icon name={s.icon} size={18}/></div>
                {s.name}
              </div>
              <span className="badge badge-ok">live</span>
            </div>
            <div className="muted" style={{ fontSize: 12 }}>Local memory · Chroma · 5min sync</div>
            <div className="swarm-meta">
              <span><strong>{s.bees}</strong> bees</span>
              <span><strong>{s.tasks}</strong> tasks</span>
              <span><strong>{s.latency}</strong> avg</span>
            </div>
          </div>
        ))}
      </div>

      {/* Waggle + Workflows */}
      <div className="cols-2" style={{ marginBottom: 32 }}>
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Waggle dance feed</h3>
              <p className="desc">Signals across swarms — from hive tasks</p>
            </div>
            <span className="badge badge-purple">{waggleEvents.length} new</span>
          </div>
          <div className="col gap-4">
            {waggleEvents.map((e,i)=>(
              <div key={i} className="row gap-3" style={{ alignItems: "flex-start" }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--gold)", marginTop: 8, boxShadow: "0 0 8px rgba(253,185,39,0.5)" }}></div>
                <div className="flex-1">
                  <div className="row gap-2" style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 4 }}>
                    <span style={{ color: "var(--gold)" }}>{e.from}</span>
                    <Icon name="arrowRight" size={10}/>
                    <span style={{ color: "var(--purple-bright)" }}>{e.to}</span>
                    <span style={{ marginLeft: "auto" }}>{e.time} ago</span>
                  </div>
                  <div style={{ fontSize: 14 }}>{e.msg}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <h3>Workflows</h3>
              <p className="desc">DAG executions · auto-decomposed from tasks</p>
            </div>
            <Btn variant="ghost" size="sm" icon="plus">New flow</Btn>
          </div>
          <div className="col gap-4">
            {workflows.map((w,i)=>(
              <div key={i}>
                <div className="row-between" style={{ marginBottom: 8 }}>
                  <div className="row gap-2">
                    <span className={`badge badge-${w.state==="running"?"info":w.state==="queued"?"warn":"ok"}`}>{w.state}</span>
                    <span style={{ fontSize: 14, fontWeight: 500 }}>{w.name}</span>
                  </div>
                  <span style={{ fontSize: 12, color: "var(--text-3)" }}>{w.agents} agents · {w.eta}</span>
                </div>
                <div className="bar-track" style={{ height: 6 }}><div className="bar-fill" style={{ width: `${w.progress}%` }}></div></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent suggestions */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div>
            <h2>Agent suggestions</h2>
            <p className="desc">Self-proposed improvements from reflection cycles · approve to apply, reject to log.</p>
          </div>
          <span className="badge badge-purple">{suggestions.length} pending</span>
        </div>
        <div className="col gap-3">
          {suggestions.map(s => (
            <div key={s.id} className="row-between wrap" style={{ padding: 14, border: "1px solid var(--line)", borderRadius: 12, gap: 12 }}>
              <div className="row gap-3 flex-1" style={{ alignItems: "flex-start" }}>
                <span className={`badge ${s.impact==="high"?"badge-gold":"badge-info"}`}>{s.impact} impact</span>
                <div className="flex-1">
                  <div style={{ fontSize: 14 }}>{s.text}</div>
                  <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>proposed by <span style={{ color: "var(--gold)" }}>{s.from}</span></div>
                </div>
              </div>
              <div className="row gap-2">
                <Btn variant="ghost" size="sm" icon="x">Reject</Btn>
                <Btn variant="primary" size="sm" icon="check">Approve</Btn>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Queen mission */}
      <div className="action-banner">
        <div className="row-between wrap" style={{ marginBottom: 16, gap: 12 }}>
          <div>
            <h2 style={{ color: "var(--gold)" }}>Queen mission</h2>
            <p className="muted">Submit a brief — the 7-step flow runs and Ballroom opens with live transcript & voice.</p>
          </div>
          <span className="badge badge-gold">7-step flow</span>
        </div>
        <textarea className="textarea" placeholder="What should the hive do?  e.g. Research top 5 voice-AI competitors, evaluate, and draft a positioning memo." value={mission} onChange={e=>setMission(e.target.value)} style={{ minHeight: 120 }}/>
        <div className="row-between wrap mt-4">
          <span className="muted">Open full New-task screen (step preview · recipe · submit)</span>
          <div className="row gap-2">
            <Btn variant="ghost" size="sm" icon="mic">Voice brief</Btn>
            <Btn variant="primary" icon="play">Run mission</Btn>
          </div>
        </div>
      </div>
    </>
  );
};

Object.assign(window, { LoginScreen, DashboardScreen });
