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
    <section className="rounded-2xl border border-magenta/30 bg-black/35 p-5 shadow-[0_0_32px_rgba(255,0,170,0.18)]">
      <header className="mb-4 flex flex-col gap-1">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-magenta">
          recent waggle dances
        </h2>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-cyan/70">
          live hive relay · gossip decays after global sync pulses
        </p>
      </header>
      <ul className="space-y-3">
        {dances.map((d) => (
          <li key={d.ts + d.signal} className="border-l-2 border-pollen/60 pl-3">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#FFB800]">
              {d.from_swarm} · {d.signal}
            </p>
            <p className="text-sm text-[#CCFFFF]">{d.topic}</p>
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-cyan/50">
              {new Date(d.ts).toISOString()}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
