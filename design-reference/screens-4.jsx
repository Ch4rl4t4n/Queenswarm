/* Foragers + Ballroom + Settings + Manual screens */

const ForagersScreen = () => {
  const sources = [
    { name: "YouTube · AI research channel", type: "youtube", schedule: "every 1h", status: "ok", lastRun: "12m ago", items: 124 },
    { name: "RSS · TechCrunch enterprise",   type: "rss",     schedule: "every 30m", status: "ok", lastRun: "4m ago",  items: 312 },
    { name: "API · Hacker News top",         type: "api",     schedule: "every 15m", status: "ok", lastRun: "8m ago",  items: 89 },
    { name: "RSS · Stratechery",             type: "rss",     schedule: "every 6h",  status: "warn", lastRun: "5h ago",  items: 47 },
    { name: "API · Product Hunt daily",      type: "api",     schedule: "daily 09:00", status: "ok", lastRun: "1h ago", items: 28 },
    { name: "YouTube · Crypto news roll",    type: "youtube", schedule: "hourly", status: "ok", lastRun: "22m ago", items: 156 },
  ];

  return (
    <>
      <PageHeader
        title="Foragers"
        desc="Data-collectors that feed HiveMind — schedule them, watch them ingest, then auto-spawn agents from harvested context."
        actions={<>
          <Btn variant="ghost" size="sm" icon="refresh">Run all now</Btn>
          <Btn variant="primary" size="sm" icon="plus">New forager</Btn>
        </>}
      />

      <div className="stat-grid">
        <Stat label="Active foragers" value="12" icon="foragers" iconClass="purple" foot="3 paused · 1 error"/>
        <Stat label="Items ingested · 24h" value="2,841" icon="pollen" foot="+18% vs avg" trend={{ dir: "up", text: "+18%" }}/>
        <Stat label="HiveMind chunks" value="48.2K" icon="knowledge" iconClass="cyan" foot="embedded last 7d"/>
        <Stat label="Auto-spawned bees" value="36" icon="agents" iconClass="green" foot="routed to swarms"/>
      </div>

      <div className="card mt-6">
        <div className="card-header">
          <div>
            <h2>Forager configurations</h2>
            <p className="desc">YouTube / RSS / API · periodicity · HiveMind ingest · auto-spawn rules.</p>
          </div>
          <div className="row gap-2">
            <button className="chip active">All · 12</button>
            <button className="chip">Active · 8</button>
            <button className="chip">Paused · 3</button>
            <button className="chip">Errors · 1</button>
          </div>
        </div>

        <table className="table">
          <thead><tr><th>Source</th><th>Type</th><th>Schedule</th><th>Last run</th><th>Items</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {sources.map((s,i)=>(
              <tr key={i}>
                <td className="task-name">{s.name}</td>
                <td><span className="badge badge-purple">{s.type}</span></td>
                <td className="mono" style={{ fontSize: 12 }}>{s.schedule}</td>
                <td className="muted">{s.lastRun}</td>
                <td>{s.items}</td>
                <td><span className={`badge ${s.status==="ok"?"badge-ok":"badge-warn"}`}>{s.status}</span></td>
                <td><div className="row gap-2"><Btn variant="ghost" size="sm" icon="play">Run</Btn><Btn variant="ghost" size="sm" icon="edit">Edit</Btn></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card mt-6">
        <div className="card-header">
          <div><h3>Auto-spawn rules</h3><p className="desc">When a forager finds X items matching a query, spawn a ScoutBee in target swarm.</p></div>
          <Btn variant="ghost" size="sm" icon="plus">Add rule</Btn>
        </div>
        <div className="col gap-3">
          {[
            { when: "RSS · TechCrunch finds 5+ items in 'AI agents'", spawn: "ScoutBee → Scout swarm", cooldown: "1h" },
            { when: "YouTube crypto roll finds 'rate cut' or 'CPI'", spawn: "EvaluatorBee → Eval swarm", cooldown: "30m" },
            { when: "API · HN top finds story with > 800 points", spawn: "ReporterBee → Action swarm", cooldown: "2h" },
          ].map((r,i)=>(
            <div key={i} className="row-between" style={{ padding: "10px 12px", border: "1px solid var(--line)", borderRadius: 12, gap: 12, flexWrap: "wrap" }}>
              <div className="row gap-3 flex-1" style={{ alignItems: "center" }}>
                <span className="badge badge-info">when</span>
                <div className="flex-1">
                  <div style={{ fontSize: 13 }}>{r.when}</div>
                  <div className="muted" style={{ fontSize: 11 }}>→ spawn <span style={{ color: "var(--gold)" }}>{r.spawn}</span> · cooldown {r.cooldown}</div>
                </div>
              </div>
              <Toggle on={true} onChange={()=>{}}/>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

/* ---------- BALLROOM ---------- */
const BallroomScreen = () => {
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState("orchestrator");
  const [filters, setFilters] = useState([
    { id: "f1", name: "Brainstorm", text: "Brainstorm 5 ideas for: " },
    { id: "f2", name: "Code review", text: "Code review this diff with focus on: " },
    { id: "f3", name: "Daily sync", text: "Daily sync — what changed in the last 24h?" },
    { id: "f4", name: "Risk check", text: "Run a risk check before shipping: " },
  ]);
  const [editingFilter, setEditingFilter] = useState(null);
  const [voiceSec, setVoiceSec] = useState(42);
  const voiceMax = 900; // 15 min
  const voicePct = (voiceSec/voiceMax)*100;
  const voiceCost = (voiceSec * 0.001).toFixed(3);

  const history = [
    { name: "Onboarding A/B insights",  time: "now",       active: true,  pinned: true },
    { name: "Calendly OAuth handshake", time: "1h",        pinned: true },
    { name: "Q3 retro synthesis",       time: "yesterday" },
    { name: "Cost routing decisions",   time: "2d" },
    { name: "Vendor catalog drift",     time: "3d" },
    { name: "Pricing simulation",       time: "4d" },
    { name: "Knowledge graph audit",    time: "5d" },
  ];

  const participants = [
    { c: "👑", live: true,  who: "Orchestrator" },
    { c: "📜", live: true,  who: "Scribe" },
    { c: "🛡", live: true,  who: "Sentinel" },
    { c: "🔮", live: false, who: "Oracle" },
    { c: "⚒",  live: true,  who: "Forge" },
  ];

  const msgs = [
    { from: "system", time: "21:12:53", text: "Ball-room channel synchronized — imitation engine narrating completions." },
    { from: "Queen",  time: "21:12:54", text: "🐝 Ball-room ready — Scout swarm has fresh nectar from onboarding A/B. Want me to summarize or hand off to Eval?" },
    { from: "you",    time: "21:13:18", text: "Summarize then route to Eval for scoring against last quarter's baseline." },
    { from: "Scribe", time: "21:13:22", text: "Drafting summary — three findings, 142 events, drop-off concentrates on step 4 (verification). Confidence 0.87." },
    { from: "Sentinel", time: "21:13:51", text: "Scoring received summary against Q2 baseline. Improvement on drop-off rate: -14%. Cost envelope: $1.20." },
    { from: "Queen",  time: "21:14:02", text: "Recommending we ship variant B to 25%. Awaiting your approve." },
  ];

  const addFilter = () => {
    const name = `Filter ${filters.length+1}`;
    setFilters([...filters, { id: `f${Date.now()}`, name, text: "" }]);
    setEditingFilter(`f${Date.now()}`);
  };
  const removeFilter = (id) => setFilters(filters.filter(f=>f.id !== id));
  const applyFilter = (f) => setDraft(prev => prev + f.text);
  const saveFilter = (id, name, text) => {
    setFilters(filters.map(f => f.id===id ? { ...f, name: name.slice(0,20), text } : f));
    setEditingFilter(null);
  };

  return (
    <>
      <PageHeader
        title="Ballroom"
        desc="Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration."
        status="WS live · 38ms"
        actions={<>
          <Btn variant="ghost" size="sm" icon="agents">Supervisor sessions</Btn>
          <Btn variant="ghost" size="sm" icon="dashboard">Dashboard</Btn>
        </>}
      />

      {/* Participants strip */}
      <div className="card card-tight" style={{ marginBottom: 20 }}>
        <div className="row-between wrap" style={{ gap: 12 }}>
          <div className="row gap-4" style={{ alignItems: "center" }}>
            <span className="label-kicker">Participants</span>
            <div className="participants">
              {participants.map((p,i)=>(
                <div key={i} className="participant" title={p.who}>
                  {p.c}{p.live && <span className="live"></span>}
                </div>
              ))}
            </div>
            <span className="muted" style={{ fontSize: 12 }}>{participants.filter(p=>p.live).length}/{participants.length} live</span>
          </div>
          <div className="row gap-2">
            <span className="badge badge-ok">LIVE</span>
            <span className="badge badge-info">WS connected</span>
          </div>
        </div>
      </div>

      <div className="chat-wrap">
        {/* History */}
        <div className="chat-side">
          <div className="row-between">
            <span className="label-kicker">Chat history · {history.length}</span>
            <Btn variant="ghost" size="sm" icon="plus">New</Btn>
          </div>
          <div className="col gap-2" style={{ maxHeight: 480, overflowY: "auto" }}>
            {history.map((h,i)=>(
              <div key={i} className="card card-tight" style={{
                padding: 12,
                background: h.active ? "linear-gradient(135deg, rgba(126,63,190,0.18), rgba(253,185,39,0.06))" : "rgba(255,255,255,0.02)",
                borderColor: h.active ? "rgba(253,185,39,0.35)" : "var(--line)",
                cursor: "pointer"
              }}>
                <div className="row-between">
                  <div className="row gap-2">
                    {h.pinned && <Icon name="pin" size={12}/>}
                    <div style={{ fontWeight: 500, fontSize: 13 }}>{h.name}</div>
                  </div>
                  <span className="muted" style={{ fontSize: 10 }}>{h.time}</span>
                </div>
                {h.active && (
                  <div className="row gap-1 mt-2 wrap">
                    <button className="chip" style={{ padding: "3px 8px", fontSize: 10 }}><Icon name="pin" size={10}/></button>
                    <button className="chip" style={{ padding: "3px 8px", fontSize: 10 }}><Icon name="edit" size={10}/></button>
                    <button className="chip" style={{ padding: "3px 8px", fontSize: 10 }}><Icon name="trash" size={10}/></button>
                  </div>
                )}
              </div>
            ))}
          </div>
          <Btn variant="ghost" size="sm" icon="trash">Clear all</Btn>
        </div>

        <div className="chat-main">
          <div className="chat-header">
            <div className="row gap-3">
              <div className="msg-avatar">🐝</div>
              <div>
                <div style={{ fontWeight: 600 }}>Onboarding A/B insights</div>
                <div className="muted" style={{ fontSize: 12 }}>5 agents present · 142 msgs · est. cost $0.84</div>
              </div>
            </div>
            <div className="row gap-2">
              <Btn variant="ghost" size="sm" icon="integrations">Ecosystem hub</Btn>
              <Btn variant="ghost" size="sm" icon="refresh">Refresh</Btn>
              <Btn variant="ghost" size="sm" icon="x">End session</Btn>
            </div>
          </div>

          <div className="chat-body">
            {msgs.map((m,i)=>(
              <div key={i} className={`msg ${m.from==="you"?"me":""}`}>
                <div className="msg-avatar">{m.from==="you"?"You":m.from==="system"?"⚙":m.from==="Queen"?"👑":m.from==="Scribe"?"📜":"🛡"}</div>
                <div className="msg-body">
                  <div className="msg-meta">
                    <span className="who">{m.from === "you" ? "You" : m.from}</span>
                    <span>{m.time}</span>
                  </div>
                  <div className="msg-bubble">{m.text}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Filters strip (CRUD) */}
          <div style={{ padding: "12px 24px", borderTop: "1px solid var(--line)" }}>
            <div className="row-between mb-3" style={{ marginBottom: 8 }}>
              <span className="label-kicker">Filters · quick prompts</span>
              <div className="row gap-2">
                <Btn variant="ghost" size="sm" icon="plus" onClick={addFilter}>Add</Btn>
                <Btn variant="ghost" size="sm">Restore defaults</Btn>
                <Btn variant="ghost" size="sm" icon="trash">Clear all</Btn>
              </div>
            </div>
            <div className="row gap-2 wrap">
              {filters.map(f => editingFilter===f.id ? (
                <div key={f.id} className="row gap-2" style={{ padding: 4, background: "rgba(7,3,15,0.6)", borderRadius: 999, border: "1px solid var(--gold)" }}>
                  <input className="input" style={{ width: 140, padding: "4px 10px", fontSize: 12 }} defaultValue={f.name} maxLength={20} id={`fn-${f.id}`}/>
                  <input className="input" style={{ width: 220, padding: "4px 10px", fontSize: 12 }} defaultValue={f.text} placeholder="Prompt text…" id={`ft-${f.id}`}/>
                  <Btn variant="primary" size="sm" icon="save" onClick={()=>saveFilter(f.id, document.getElementById(`fn-${f.id}`).value, document.getElementById(`ft-${f.id}`).value)}>Save</Btn>
                </div>
              ) : (
                <div key={f.id} className="filter-pill">
                  <span onClick={()=>applyFilter(f)} style={{ cursor: "pointer" }}>{f.name}</span>
                  <button onClick={()=>setEditingFilter(f.id)} title="Edit"><Icon name="edit" size={11}/></button>
                  <button onClick={()=>removeFilter(f.id)} title="Remove">×</button>
                </div>
              ))}
            </div>
          </div>

          <div className="chat-input">
            <input className="input" placeholder="Send to swarm…  (tip: use @AgentName)" value={draft} onChange={e=>setDraft(e.target.value)}/>
            <Btn variant="ghost" size="md" icon="mic">Voice</Btn>
            <Btn variant="primary" size="md" icon="send">Send</Btn>
          </div>

          {/* Voice cost guardrails */}
          <div style={{ borderTop: "1px solid var(--line)", padding: "16px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="row-between wrap">
              <span className="label-kicker">Voice chat mode</span>
              <div className="row gap-2">
                <button className={`chip ${mode==="orchestrator"?"active":""}`} onClick={()=>setMode("orchestrator")}>Orchestrator</button>
                <button className={`chip ${mode==="swarm"?"active":""}`} onClick={()=>setMode("swarm")}>Swarm</button>
              </div>
            </div>

            <div className="row-between" style={{ fontSize: 12 }}>
              <div className="row gap-3" style={{ alignItems: "center" }}>
                <div className="voice-bars"><span></span><span></span><span></span><span></span><span></span></div>
                <span style={{ color: "var(--text)" }}>Voice capture · <span className="mono">{Math.floor(voiceSec/60)}:{(voiceSec%60).toString().padStart(2,"0")}</span></span>
              </div>
              <span style={{ color: "var(--gold)", fontWeight: 600 }}>est. ${voiceCost}</span>
            </div>

            <div className="voice-gauge">
              <div className="voice-gauge-fill" style={{ width: `${voicePct}%` }}></div>
              <div className="voice-marker warn" style={{ left: `${(480/voiceMax)*100}%` }}></div>
              <div className="voice-marker err"  style={{ left: `${(780/voiceMax)*100}%` }}></div>
            </div>
            <div className="row-between" style={{ fontSize: 10, color: "var(--text-3)" }}>
              <span>0:00</span>
              <span style={{ color: "var(--warn)" }}>⚠ soft warn · 8:00</span>
              <span style={{ color: "var(--err)" }}>⚠ pre-cap · 13:00</span>
              <span>hard cap 15:00</span>
            </div>

            <div className="muted" style={{ fontSize: 12, fontStyle: "italic", borderLeft: "2px solid var(--purple-bright)", paddingLeft: 12 }}>
              Live transcript will appear here. STT routed Grok → Deepgram → OpenAI Whisper (auto-fallback).
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

/* ---------- SETTINGS ---------- */
const SettingsScreen = () => {
  const [lang, setLang] = useState("ENG");
  const [active, setActive] = useState("security");
  const [vad, setVad] = useState(0.7);
  const [silence, setSilence] = useState(100);
  const [twofa, setTwofa] = useState(true);

  const sections = [
    { id: "security", label: "Security · 2FA", icon: "shield" },
    { id: "billing", label: "Billing · Usage", icon: "coin" },
    { id: "team", label: "Team · RBAC", icon: "agents" },
    { id: "sharing", label: "Public sharing", icon: "globe" },
    { id: "voice", label: "AI · Voice keys", icon: "mic" },
    { id: "notify", label: "Notifications", icon: "alert" },
    { id: "api", label: "API · external keys", icon: "keyIcon" },
    { id: "audit", label: "Audit log", icon: "list" },
  ];

  const keys = [
    { provider: "Grok · xAI", chip: "xAI", label: "Primary", saved: "••••••xGHS", desc: "Primary routing — persisted in hive vault." },
    { provider: "Claude · Anthropic", chip: "CL", label: "Primary", saved: "••••••0AAA", desc: "Admin-only unless env already supplies credential." },
    { provider: "OpenAI · GPT-4o mini", chip: "GPT", label: "Fallback", saved: "••••••mini", desc: "Fallback for low-priority traffic." },
    { provider: "Deepgram STT", chip: "DG", label: "Voice STT", saved: "••••••Z7gp", desc: "Speech-to-text · second priority after Grok." },
    { provider: "ElevenLabs TTS", chip: "EL", label: "Voice TTS", saved: "••••••Vk83", desc: "Text-to-speech · second priority after Grok." },
  ];

  const team = [
    { name: "Lukáš H.",     email: "lukas@queenswarm.love", role: "owner", added: "2024-08-12" },
    { name: "Mia D.",       email: "mia@queenswarm.love",   role: "admin", added: "2024-09-04" },
    { name: "Daniel O.",    email: "daniel@queenswarm.love",role: "member", added: "2025-01-18" },
    { name: "Petra V.",     email: "petra@queenswarm.love", role: "viewer", added: "2025-02-22" },
    { name: "guest@external", email: "guest@external.io",   role: "guest", added: "2025-04-10" },
  ];

  const audit = [
    { time: "21:12:53", who: "Lukáš H.", action: "Approved task T-9420 · Synthesize Q3 retro", ip: "10.0.0.42" },
    { time: "21:08:14", who: "Mia D.",   action: "Rotated Grok API key", ip: "192.168.1.18" },
    { time: "20:47:02", who: "system",   action: "Auto-rebalanced hive · 2 bees moved from Sim → Eval", ip: "—" },
    { time: "19:32:28", who: "Daniel O.",action: "Created bee · LearnerBee-7 in Action swarm", ip: "10.0.0.71" },
    { time: "18:11:55", who: "Lukáš H.", action: "Enabled 2FA for tenant", ip: "10.0.0.42" },
  ];

  return (
    <>
      <PageHeader
        title="Settings"
        desc="Security · Billing · Team RBAC · Sharing · AI vault · Notifications · API keys · Audit"
        actions={<>
          <div className="row gap-1" style={{ padding: 4, background: "rgba(255,255,255,0.04)", borderRadius: 999, border: "1px solid var(--line)" }}>
            {["ENG","SVK"].map(l => (
              <button key={l} onClick={()=>setLang(l)} className="chip" style={{
                background: lang===l ? "var(--grad-primary)" : "transparent",
                color: lang===l ? "#1A0E2E" : "var(--text-2)",
                fontWeight: 600,
                border: "none",
                padding: "6px 16px"
              }}>{l}</button>
            ))}
          </div>
        </>}
      />

      <div className="row gap-2 wrap" style={{ marginBottom: 24 }}>
        {sections.map(s => (
          <button key={s.id} className={`chip ${active===s.id?"active":""}`} onClick={()=>setActive(s.id)}>
            <Icon name={s.icon} size={12}/>
            {s.label}
          </button>
        ))}
      </div>

      {active === "security" && (
        <div className="card-section">
          <div className="card">
            <div className="card-header">
              <div>
                <h2>Two-factor authentication</h2>
                <p className="desc">TOTP-based — Authenticator app, backup codes, advanced policies per RBAC role.</p>
              </div>
              <Toggle on={twofa} onChange={setTwofa}/>
            </div>
            {twofa && (
              <div className="cols-2">
                <div>
                  <div className="label-kicker mb-3">Authenticator app</div>
                  <div style={{ padding: 16, background: "rgba(7,3,15,0.5)", borderRadius: 12, display: "grid", placeItems: "center" }}>
                    <div style={{ width: 160, height: 160, background: "white", padding: 8, borderRadius: 8 }}>
                      <svg viewBox="0 0 144 144" width="144" height="144">
                        {Array.from({ length: 18*18 }).map((_,i)=>(
                          Math.random()>0.5 && <rect key={i} x={(i%18)*8} y={Math.floor(i/18)*8} width="8" height="8" fill="#1A0E2E"/>
                        ))}
                      </svg>
                    </div>
                  </div>
                  <div className="mono mt-3" style={{ fontSize: 12, color: "var(--text-3)", textAlign: "center" }}>JBSWY3DPEHPK3PXP</div>
                </div>
                <div>
                  <div className="label-kicker mb-3">Backup codes</div>
                  <p className="muted">Store these somewhere safe — each works once.</p>
                  <div className="cols-2 mt-3" style={{ gap: 8 }}>
                    {["8KQF-RW2A","9XPL-NM7B","ZT4P-VC81","BH3Q-LM92","RNK7-2DXV","WP8X-QL44","MV5R-HT38","CY9B-PK21"].map(c=>(
                      <div key={c} className="mono" style={{ fontSize: 12, padding: "8px 12px", background: "rgba(7,3,15,0.6)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--gold)" }}>{c}</div>
                    ))}
                  </div>
                  <div className="row gap-2 mt-4"><Btn variant="ghost" size="sm" icon="refresh">Regenerate</Btn><Btn variant="ghost" size="sm" icon="download">Download .txt</Btn></div>
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <h3>Session policy</h3>
            <div className="col gap-3 mt-4">
              <div className="row-between"><div><div style={{ fontWeight: 500 }}>JWT access token TTL</div><div className="muted">Currently 15 minutes</div></div><select className="select" style={{ width: 140 }}><option>5 min</option><option>15 min</option><option>60 min</option></select></div>
              <div className="row-between"><div><div style={{ fontWeight: 500 }}>Refresh token TTL</div><div className="muted">Currently 30 days</div></div><select className="select" style={{ width: 140 }}><option>7 days</option><option>30 days</option><option>90 days</option></select></div>
              <div className="row-between"><div><div style={{ fontWeight: 500 }}>Rate limit (per user)</div><div className="muted">100 req/min sliding window</div></div><span className="badge badge-ok">enforced</span></div>
              <div className="row-between"><div><div style={{ fontWeight: 500 }}>OAuth consent (PKCE)</div><div className="muted">Redis state TTL 5 min</div></div><span className="badge badge-ok">enabled</span></div>
            </div>
          </div>
        </div>
      )}

      {active === "voice" && (
        <div className="card-section">
          <div className="card">
            <div className="card-header"><div><h2>Preferred voice provider · STT / TTS</h2><p className="desc">Credentials route through <span className="mono" style={{ color:"var(--gold)" }}>POST /api/v1/llm-keys</span> — masked values never round-trip plaintext.</p></div></div>

            <div className="cols-2" style={{ marginBottom: 20 }}>
              <div className="input-group"><label>STT priority</label>
                <select className="select"><option>Auto · Grok → Deepgram → OpenAI</option><option>Grok only</option><option>Deepgram only</option><option>OpenAI Whisper only</option></select>
              </div>
              <div className="input-group"><label>TTS priority</label>
                <select className="select"><option>Auto · Grok → ElevenLabs → OpenAI</option><option>Grok only</option><option>ElevenLabs only</option><option>OpenAI only</option></select>
              </div>
            </div>

            <div className="input-group mb-5">
              <label>Latency mode</label>
              <select className="select"><option>Fast · lower latency</option><option>Balanced</option><option>Deliberate</option></select>
            </div>

            <div className="cols-2" style={{ marginBottom: 20 }}>
              <div className="range-row">
                <div className="range-head"><span>VAD threshold</span><span className="range-val">{vad.toFixed(2)}</span></div>
                <input type="range" className="slider" min="0" max="1" step="0.01" value={vad} onChange={e=>setVad(parseFloat(e.target.value))}/>
                <span className="muted" style={{ fontSize: 11 }}>Voice sensitivity · higher catches more speech</span>
              </div>
              <div className="range-row">
                <div className="range-head"><span>Silence duration (ms)</span><span className="range-val">{silence}</span></div>
                <input type="range" className="slider" min="50" max="2000" step="10" value={silence} onChange={e=>setSilence(parseInt(e.target.value))}/>
                <span className="muted" style={{ fontSize: 11 }}>Time before utterance commits</span>
              </div>
            </div>

            <div className="cols-3" style={{ marginBottom: 20 }}>
              <div className="input-group"><label>Voice profile</label><select className="select"><option>Sol</option><option>Luna</option><option>Nova</option><option>Atlas</option></select></div>
              <div className="input-group"><label>Voice tone</label><select className="select"><option>Authoritative</option><option>Friendly</option><option>Concise</option></select></div>
              <div className="input-group"><label>Voice language</label><select className="select"><option>English (en)</option><option>Slovak (sk)</option></select></div>
            </div>
            <Btn variant="primary" icon="save">Save voice preferences</Btn>
          </div>

          {keys.map(k => (
            <div key={k.provider} className="card">
              <div className="row-between wrap" style={{ marginBottom: 12 }}>
                <div className="row gap-3">
                  <div className="int-logo" style={{ width: 42, height: 42, fontWeight: 700 }}>{k.chip}</div>
                  <div>
                    <div style={{ fontWeight: 600 }}>{k.provider}</div>
                    <p className="muted" style={{ fontSize: 12 }}>{k.desc}</p>
                  </div>
                </div>
                <div className="row gap-2">
                  <Btn variant="ghost" size="sm" icon="play">Test</Btn>
                  <Btn variant="ghost" size="sm" icon="trash">Remove</Btn>
                </div>
              </div>
              <div className="cols-2">
                <div className="input-group"><label>Friendly label</label><input className="input" defaultValue={k.label}/></div>
                <div className="input-group"><label>Saved secret</label><input className="input mono" defaultValue={k.saved} readOnly/></div>
              </div>
              <div className="input-group mt-4"><label>Paste new API secret</label><input className="input" placeholder="Paste new API secret"/></div>
              <div className="mt-4"><Btn variant="primary" size="sm" icon="check">Save key</Btn></div>
            </div>
          ))}
        </div>
      )}

      {active === "team" && (
        <div className="card-section">
          <div className="card">
            <div className="card-header">
              <div><h2>Team & RBAC</h2><p className="desc">5 roles — owner / admin / member / viewer / guest. Permissions: supervisor:*, team:manage, resources:share.</p></div>
              <Btn variant="primary" size="sm" icon="plus">Invite member</Btn>
            </div>
            <table className="table">
              <thead><tr><th>Member</th><th>Role</th><th>Added</th><th></th></tr></thead>
              <tbody>
                {team.map(m=>(
                  <tr key={m.email}>
                    <td>
                      <div className="task-name">{m.name}</div>
                      <div className="muted" style={{ fontSize: 11 }}>{m.email}</div>
                    </td>
                    <td><span className={`badge ${m.role==="owner"?"badge-gold":m.role==="admin"?"badge-purple":m.role==="member"?"badge-info":m.role==="viewer"?"badge-ok":"badge-warn"}`}>{m.role}</span></td>
                    <td className="muted">{m.added}</td>
                    <td><div className="row gap-2"><Btn variant="ghost" size="sm" icon="edit">Role</Btn><Btn variant="ghost" size="sm" icon="trash">Remove</Btn></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Permissions matrix</h3>
            <table className="table mt-4">
              <thead><tr><th>Permission</th><th>Owner</th><th>Admin</th><th>Member</th><th>Viewer</th><th>Guest</th></tr></thead>
              <tbody>
                {[
                  ["supervisor:*", "✓","✓","✓","—","—"],
                  ["agents:write", "✓","✓","✓","—","—"],
                  ["team:manage",  "✓","✓","—","—","—"],
                  ["resources:share","✓","✓","✓","—","—"],
                  ["billing:view", "✓","✓","—","—","—"],
                ].map((row,i)=>(
                  <tr key={i}>
                    <td className="mono task-name">{row[0]}</td>
                    {row.slice(1).map((c,j)=><td key={j} style={{ color: c==="✓"?"var(--ok)":"var(--text-3)", textAlign: "center" }}>{c}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {active === "audit" && (
        <div className="card">
          <div className="card-header">
            <div><h2>Audit log</h2><p className="desc">Admin actions, key rotations, hive auto-rebalances · 90-day retention.</p></div>
            <div className="row gap-2">
              <select className="select" style={{ width: 140 }}><option>All actions</option><option>Auth</option><option>Keys</option><option>Hive</option></select>
              <Btn variant="ghost" size="sm" icon="download">Export</Btn>
            </div>
          </div>
          <div>
            {audit.map((a,i)=>(
              <div key={i} className="audit-row">
                <span className="audit-time">{a.time}</span>
                <div>
                  <span className="audit-who">{a.who}</span>
                  <span className="audit-action"> · {a.action}</span>
                </div>
                <span className="muted mono" style={{ fontSize: 11 }}>{a.ip}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {active === "billing" && (
        <div className="card-section">
          <div className="card">
            <div className="card-header"><div><h2>Plan · Hive Pro</h2><p className="desc">Unlimited bees · 4 swarms · 50K HiveMind chunks · $99/mo</p></div><Btn variant="ghost" size="sm">Upgrade</Btn></div>
            <div className="cols-3 mt-4">
              <Stat label="Spend · this month" value="$2,418" icon="coin"/>
              <Stat label="Tasks run" value="1,842" icon="bolt" iconClass="cyan"/>
              <Stat label="HiveMind storage" value="48.2 / 50K" icon="knowledge" iconClass="purple" foot="96% used"/>
            </div>
          </div>
        </div>
      )}

      {(active==="sharing" || active==="notify" || active==="api") && (
        <div className="card">
          <div className="card-header"><div><h2>{sections.find(s=>s.id===active)?.label}</h2><p className="desc">Configure {active} — settings persist to encrypted vault.</p></div></div>
          <div className="empty">
            <div className="empty-icon">⚙</div>
            <div>Section ready · select an option above to configure.</div>
          </div>
        </div>
      )}
    </>
  );
};

/* ---------- MANUAL ---------- */
const ManualScreen = () => {
  const [open, setOpen] = useState(0);

  const sections = [
    { title: "1. Quick start", body: ["After login, start on Dashboard — check status, then spawn sessions.","Sign in via /login → land on /dashboard.","Open Agents → start first Supervisor session with one concrete goal.","Create a related task in Tasks so the outcome is tracked.","Search Knowledge first — reuse existing outputs (retrieval-first).","If something fails, open Ballroom and coordinate live."] },
    { title: "2. Main sections", body: ["Dashboard is the command center.","Agents drives Supervisor sessions, browser harness, and hierarchy.","Tasks covers execution, workflows, jobs, simulations, routines.","Knowledge holds context (HiveMind), outputs, recipes, and dreaming.","Integrations manages connectors, tools marketplace, plugins, external projects.","Ballroom is the realtime channel — text + voice + filters CRUD.","Settings holds security/2FA, team RBAC, billing, AI keys, notifications, API keys, audit log."] },
    { title: "3. Bee roles", body: ["ScraperBee · pulls data from foragers.","EvaluatorBee · scores and ranks outputs.","SimulatorBee · runs sandboxed cost / behavior sims.","ReporterBee · narrates results into Ballroom.","TraderBee · executes paper or live actions.","MarketerBee + BlogWriterBee + SocialPosterBee · creator chain.","LearnerBee · adapts from reflections, top-K imitation.","RecipeKeeperBee · curates and serves recipes.","GenericBee · catch-all when role is undecided."] },
    { title: "4. Best practices", body: ["Write prompts as Goal → Context → Constraints → Done.","Always Knowledge → search first; it's cheaper than a fresh compute run.","Reserve routines for repeatable processes; start with conservative cadence.","Use Filters in Ballroom to standardize team prompts."] },
    { title: "5. Voice providers", body: ["In Settings → AI · Voice keys, store Grok / Deepgram / OpenAI (STT) and Grok / ElevenLabs / OpenAI (TTS) keys directly — no deploy edits.","Pick STT/TTS priority (Auto or explicit). On failure, server-side fallback applies automatically.","Tune VAD threshold (sensitivity), silence duration (utterance commit), voice profile / tone / language.","Voice cost guardrails: soft warn 8min · pre-cap 13min · hard cap 15min (auto-stop)."] },
    { title: "6. Troubleshooting", body: ["Redirect to /login often means an expired session cookie.","401 = auth · 403 = RBAC / permission · 404 = route or proxy drift.","For routine failures: check active flag, interval, worker/beat health, last error detail.","Use Costs → System status for live infra health (API, Celery, Redis, Postgres, Neo4j, Chroma)."] },
  ];

  return (
    <>
      <PageHeader
        title="Manual"
        desc="Operator guide — every section, every flag, every shortcut."
        actions={<Btn variant="ghost" size="sm" icon="download">Download PDF</Btn>}
      />

      <div className="card-section">
        {sections.map((s,i)=>(
          <div key={i} className="card" style={{ cursor: "pointer" }} onClick={()=>setOpen(open===i?-1:i)}>
            <div className="row-between">
              <h2>{s.title}</h2>
              <Icon name={open===i?"chevDown":"chevRight"} size={20}/>
            </div>
            {open===i && (
              <div className="col gap-3 mt-4">
                {s.body.map((line,j) => (<p key={j} style={{ color: "var(--text-2)" }}>{line}</p>))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
};

Object.assign(window, { ForagersScreen, BallroomScreen, SettingsScreen, ManualScreen });
