/* Swarms, Costs, Leaderboard, Simulations, Monitoring screens */

/* ---------- SWARMS ---------- */
const SwarmsScreen = () => {
  const colonies = [
    { id: "colony-alpha", name: "Alpha · Onboarding Lab", swarm: "Scout", bees: 8, status: "active", pollen: 4280, queen: "Orchestrator", lastSync: "38s" },
    { id: "colony-beta",  name: "Beta · Pricing Eval",   swarm: "Eval",  bees: 12, status: "active", pollen: 5910, queen: "Sentinel",     lastSync: "1m" },
    { id: "colony-gamma", name: "Gamma · Cost Sim",      swarm: "Sim",   bees: 6,  status: "paused", pollen: 2140, queen: "Oracle",        lastSync: "11m" },
    { id: "colony-delta", name: "Delta · Auto-deploy",   swarm: "Action",bees: 14, status: "active", pollen: 7820, queen: "Forge",         lastSync: "12s" },
  ];

  const waggles = [
    { t: "21:14:22", from: "Alpha", to: "Beta",   msg: "Onboarding A/B handoff — variant B wins (+14% step-4 conversion)" },
    { t: "21:13:08", from: "Beta",  to: "Delta",  msg: "Approved for shipping · risk score 0.08 · rollout 25%" },
    { t: "21:11:50", from: "Gamma", to: "Queen",  msg: "Cost envelope nearing 80% — request rebalance" },
    { t: "21:08:14", from: "Delta", to: "Alpha",  msg: "Rolling out tooltip v3 to 25% — telemetry needed" },
    { t: "21:04:32", from: "Alpha", to: "Gamma",  msg: "Need simulation for tooltip cost under 30k DAU" },
  ];

  return (
    <>
      <PageHeader
        title="Swarms"
        desc="Colony control plane — decentralized sub-hives with local memory, global sync every 5 min."
        status="4 colonies live"
        actions={<>
          <Btn variant="ghost" size="sm" icon="refresh">Hive sync ACK</Btn>
          <Btn variant="ghost" size="sm" icon="sparkleSm">Wake all bees</Btn>
          <Btn variant="primary" size="sm" icon="plus">New colony</Btn>
        </>}
      />

      <div className="stat-grid">
        <Stat label="Colonies" value="4" icon="swarms" iconClass="purple" foot="3 active · 1 paused"/>
        <Stat label="Total bees" value="40" icon="agents" foot="36 working · 4 idle"/>
        <Stat label="Pollen pool" value="20,150" icon="pollen" iconClass="green" trend={{ dir:"up", text:"+8% 24h" }}/>
        <Stat label="Avg sync drift" value="1m 14s" icon="radio" iconClass="cyan" foot="Last global tick 38s ago"/>
      </div>

      <div className="card mt-6" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div><h2>Colonies</h2><p className="desc">Each colony is a decentralized SubSwarm running LangGraph locally; Maynard-Cross pollen rewards apply.</p></div>
        </div>
        <table className="table">
          <thead><tr><th>Colony</th><th>Swarm</th><th>Queen</th><th>Bees</th><th>Pollen</th><th>Last sync</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {colonies.map(c=>(
              <tr key={c.id}>
                <td>
                  <div className="task-name">{c.name}</div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>{c.id}</div>
                </td>
                <td><span className="badge badge-purple">{c.swarm}</span></td>
                <td><span style={{ color: "var(--gold)" }}>👑 {c.queen}</span></td>
                <td>{c.bees}</td>
                <td><span className="pollen-pill"><Icon name="pollen" size={11}/>{c.pollen.toLocaleString()}</span></td>
                <td className="muted">{c.lastSync} ago</td>
                <td><span className={`badge ${c.status==="active"?"badge-ok":"badge-warn"}`}>{c.status}</span></td>
                <td>
                  <div className="row gap-2">
                    <Btn variant="ghost" size="sm" icon={c.status==="paused"?"play":"pause"}>{c.status==="paused"?"Resume":"Pause"}</Btn>
                    <Btn variant="ghost" size="sm" icon="eye">Open</Btn>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="cols-2">
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Waggle dance feed</h3>
              <p className="desc">Realtime cross-swarm signals — backed by hive tasks topic.</p>
            </div>
            <span className="badge badge-purple">live</span>
          </div>
          <div className="col gap-3">
            {waggles.map((w,i)=>(
              <div key={i} className="row gap-3" style={{ paddingBottom: 12, borderBottom: i<waggles.length-1?"1px solid var(--line)":"none", alignItems: "flex-start" }}>
                <span className="mono" style={{ fontSize: 11, color: "var(--text-3)", flexShrink: 0, paddingTop: 2 }}>{w.t}</span>
                <div className="flex-1">
                  <div className="row gap-2" style={{ fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: "var(--gold)" }}>{w.from}</span>
                    <Icon name="arrowRight" size={10}/>
                    <span style={{ color: "var(--purple-bright)" }}>{w.to}</span>
                  </div>
                  <div style={{ fontSize: 13 }}>{w.msg}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <h3>Hive sync</h3>
              <p className="desc">Global state convergence — Celery beat tick every 5 min.</p>
            </div>
            <Btn variant="ghost" size="sm" icon="refresh">Force sync</Btn>
          </div>
          <div className="col gap-4">
            {[
              { label: "Pollen ledger", state: "synced", at: "38s ago" },
              { label: "Recipe index", state: "synced", at: "1m 12s ago" },
              { label: "HiveMind graph", state: "syncing", at: "in progress" },
              { label: "Imitation pool", state: "synced", at: "2m 04s ago" },
              { label: "Cost records", state: "synced", at: "1m ago" },
            ].map((s,i)=>(
              <div key={i} className="row-between" style={{ paddingBottom: 12, borderBottom: "1px solid var(--line)" }}>
                <div className="row gap-3">
                  <span className={`badge ${s.state==="synced"?"badge-ok":"badge-info"}`}>{s.state}</span>
                  <span style={{ fontSize: 14 }}>{s.label}</span>
                </div>
                <span className="muted" style={{ fontSize: 12 }}>{s.at}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
};

/* ---------- COSTS ---------- */
const CostsScreen = () => {
  const trend = [40,55,32,68,90,72,85,60,78,95,82,70,88,77,92,68,74,86,90,82,77,89,94,72,68,80,74,92,86,78];
  const byAgent = [
    { name: "Orchestrator", role: "Queen",   spend: 482.41, pct: 100 },
    { name: "Sentinel",    role: "Eval",    spend: 318.20, pct: 66 },
    { name: "Forge",       role: "Action",  spend: 274.55, pct: 57 },
    { name: "Scribe",      role: "Scout",   spend: 188.12, pct: 39 },
    { name: "Oracle",      role: "Sim",     spend: 142.08, pct: 29 },
    { name: "Cartographer",role: "Scout",   spend: 104.91, pct: 22 },
  ];
  const byProvider = [
    { name: "Grok · xAI",     spend: 982.40, pct: 41 },
    { name: "Claude · Anthropic", spend: 712.84, pct: 30 },
    { name: "OpenAI · GPT",   spend: 463.20, pct: 19 },
    { name: "Deepgram STT",   spend: 142.10, pct: 6 },
    { name: "ElevenLabs TTS", spend: 96.45,  pct: 4 },
  ];

  return (
    <>
      <PageHeader
        title="Costs & monitoring"
        desc="Spend trend · LLM/voice envelopes · system status · agent attribution."
        actions={<>
          <Btn variant="ghost" size="sm" icon="download">Export CSV</Btn>
          <Btn variant="primary" size="sm" icon="alert">Set budget</Btn>
        </>}
      />

      <div className="stat-grid">
        <Stat label="Spend · 30 days" value="$2,418" icon="coin" iconClass="" trend={{ dir:"down", text:"-12% vs prev 30d" }}/>
        <Stat label="Spend · today" value="$48.20" icon="bolt" foot="42% of daily envelope"/>
        <Stat label="Avg cost per task" value="$0.84" icon="chart" iconClass="cyan" trend={{ dir:"down", text:"-6% vs avg" }}/>
        <Stat label="Voice spend · 7d" value="$184.10" icon="mic" iconClass="purple" foot="Grok + Deepgram + EL"/>
      </div>

      <div className="card mt-6">
        <div className="card-header">
          <div>
            <h3>Spend trend · 30 days</h3>
            <p className="desc">Sums routed LLM spend — tasks, Ballroom chat, workflows, LLM previews.</p>
          </div>
          <div className="row gap-2">
            <button className="chip">24h</button>
            <button className="chip active">30d</button>
            <button className="chip">90d</button>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "end", gap: 4, height: 160, marginTop: 8 }}>
          {trend.map((v,i)=>(
            <div key={i} style={{
              flex: 1, height: `${v}%`,
              background: "var(--grad-mix)",
              borderRadius: 4,
              opacity: 0.55 + (i/60),
              position: "relative"
            }}/>
          ))}
        </div>
        <div className="row-between mt-3" style={{ fontSize: 11, color: "var(--text-3)" }}>
          <span>Apr 18</span><span>Apr 25</span><span>May 02</span><span>May 09</span><span>May 16</span>
        </div>
      </div>

      <div className="cols-2 mt-6">
        <div className="card">
          <div className="card-header">
            <div><h3>By agent</h3><p className="desc">Top spenders this window.</p></div>
          </div>
          <div>
            {byAgent.map(a=>(
              <div key={a.name} className="row-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                <div className="row gap-3">
                  <div className="msg-avatar" style={{ width: 28, height: 32, fontSize: 11 }}>{a.name.charAt(0)}</div>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: 13 }}>{a.name}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{a.role}</div>
                  </div>
                </div>
                <div className="col" style={{ alignItems: "flex-end", minWidth: 140 }}>
                  <div style={{ fontWeight: 600, color: "var(--gold)" }}>${a.spend.toFixed(2)}</div>
                  <div className="bar-track" style={{ width: 100, height: 4, marginTop: 4 }}>
                    <div className="bar-fill" style={{ width: `${a.pct}%` }}></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div><h3>By provider</h3><p className="desc">Cross-LLM routing breakdown.</p></div>
          </div>
          <div>
            {byProvider.map(p=>(
              <BarRow key={p.name} label={p.name} value={`$${p.spend.toFixed(2)}`} pct={p.pct}/>
            ))}
          </div>
        </div>
      </div>

      <div className="card mt-6">
        <div className="card-header">
          <div><h3>System status</h3><p className="desc">Live operator snapshot — Prometheus / Grafana metrics.</p></div>
          <Btn variant="ghost" size="sm" icon="globe">Open Grafana</Btn>
        </div>
        <div className="cols-3">
          {[
            { label: "API", value: "97.4%", state: "ok", note: "p95 142ms" },
            { label: "Celery workers", value: "8/8", state: "ok", note: "0 retries · 4 queues" },
            { label: "Redis", value: "healthy", state: "ok", note: "12MB · 0.2ms" },
            { label: "Postgres", value: "healthy", state: "ok", note: "p95 12ms · 18 connections" },
            { label: "Neo4j", value: "healthy", state: "ok", note: "128 nodes · 412 ribs" },
            { label: "Chroma", value: "syncing", state: "info", note: "ingest 38 chunks" },
          ].map((s,i)=>(
            <div key={i} className="card card-tight">
              <div className="row-between">
                <span className="label-kicker">{s.label}</span>
                <span className={`badge badge-${s.state}`}>{s.state}</span>
              </div>
              <div style={{ fontSize: 24, fontWeight: 600, color: "var(--gold)", marginTop: 8 }}>{s.value}</div>
              <div className="muted" style={{ fontSize: 11 }}>{s.note}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

/* ---------- LEADERBOARD ---------- */
const LeaderboardScreen = () => {
  const board = [
    { rank: 1, name: "Sentinel",    role: "Eval",   pollen: 5840, tasks: 142, score: "9.4", trend: "+12" },
    { rank: 2, name: "Forge",       role: "Action", pollen: 5420, tasks: 188, score: "9.1", trend: "+8" },
    { rank: 3, name: "Scribe",      role: "Scout",  pollen: 5210, tasks: 94,  score: "8.9", trend: "+4" },
    { rank: 4, name: "Orchestrator",role: "Queen",  pollen: 4980, tasks: 36,  score: "9.4", trend: "—" },
    { rank: 5, name: "Oracle",      role: "Sim",    pollen: 4112, tasks: 71,  score: "8.7", trend: "+2" },
    { rank: 6, name: "Cartographer",role: "Scout",  pollen: 3840, tasks: 88,  score: "8.4", trend: "-1" },
    { rank: 7, name: "Beacon",      role: "Action", pollen: 3220, tasks: 102, score: "8.2", trend: "+5" },
    { rank: 8, name: "Loom",        role: "Scout",  pollen: 2980, tasks: 60,  score: "8.6", trend: "+1" },
    { rank: 9, name: "Nectar",      role: "Eval",   pollen: 2540, tasks: 48,  score: "9.0", trend: "+3" },
    { rank: 10,name: "Compass",     role: "Sim",    pollen: 1880, tasks: 35,  score: "7.9", trend: "-2" },
  ];

  return (
    <>
      <PageHeader
        title="Leaderboard"
        desc="Pollen ranking · Maynard-Cross allocation + performance blend · auto-feeds Imitation Engine."
        actions={<>
          <Btn variant="ghost" size="sm" icon="refresh">Recompute</Btn>
          <Btn variant="primary" size="sm" icon="sparkleSm">Run imitation pass</Btn>
        </>}
      />

      <div className="cols-3 mb-6">
        {board.slice(0,3).map((b,i)=>(
          <div key={b.name} className="card" style={{
            borderColor: i===0 ? "rgba(253,185,39,0.4)" : i===1 ? "rgba(216,201,240,0.3)" : "rgba(201,142,10,0.4)"
          }}>
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div className={`lb-rank ${i===0?"gold":i===1?"silver":"bronze"}`}>{b.rank}</div>
              <span className="pollen-pill"><Icon name="pollen" size={11}/>{b.pollen.toLocaleString()}</span>
            </div>
            <div className="row gap-3" style={{ alignItems: "center" }}>
              <div className="hex" style={{ width: 56, height: 64 }}>
                <div className="hex-inner">
                  <div className="hex-name">{b.name.charAt(0)}</div>
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 16 }}>{b.name}</div>
                <div className="muted">{b.role} · score {b.score}</div>
                <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>{b.tasks} tasks · trend {b.trend}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <div><h3>Full ranking</h3><p className="desc">Top performers feed imitation exemplars and recipe library upgrades.</p></div>
          <div className="row gap-2">
            <select className="select" style={{ width: 160 }}><option>All roles</option><option>Scout</option><option>Eval</option><option>Sim</option><option>Action</option></select>
            <select className="select" style={{ width: 140 }}><option>Last 7 days</option><option>Last 30 days</option><option>All time</option></select>
          </div>
        </div>
        <div className="col">
          {board.map(b => (
            <div key={b.name} className="lb-row">
              <div className={`lb-rank ${b.rank===1?"gold":b.rank===2?"silver":b.rank===3?"bronze":""}`}>{b.rank}</div>
              <div>
                <div style={{ fontWeight: 500 }}>{b.name} <span className="muted" style={{ fontSize: 11, marginLeft: 6 }}>{b.role}</span></div>
                <div className="muted" style={{ fontSize: 11 }}>{b.tasks} tasks · score {b.score} · trend <span style={{ color: b.trend.startsWith("-") ? "var(--err)" : "var(--ok)" }}>{b.trend}</span></div>
              </div>
              <span className="pollen-pill"><Icon name="pollen" size={11}/>{b.pollen.toLocaleString()}</span>
              <Btn variant="ghost" size="sm" icon="eye">View</Btn>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

Object.assign(window, { SwarmsScreen, CostsScreen, LeaderboardScreen });
