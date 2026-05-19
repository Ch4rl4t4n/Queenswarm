interface DanceLine {
  from_swarm: string;
  signal: string;
  topic: string;
  ts: string;
}

interface DanceStripProps {
  dances: DanceLine[];
}

export function DanceStrip({ dances }: DanceStripProps) {
  return (
    <section className="v4-card">
      <header className="v4-card-header">
        <div>
          <h3>Waggle dance feed</h3>
          <p className="desc">Live hive relay · gossip decays after global sync pulses</p>
        </div>
      </header>
      <ul className="space-y-3">
        {dances.map((d) => (
          <li key={d.ts + d.signal} className="border-l-2 border-(--qs-border-2) pl-3">
            <p className="text-sm font-medium text-pollen">
              {d.from_swarm} · {d.signal}
            </p>
            <p className="text-sm text-(--qs-text-2)">{d.topic}</p>
            <p className="text-[11px] text-(--qs-text-3)">{new Date(d.ts).toISOString()}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
