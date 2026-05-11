export const metadata = {
  title: "Plugins · Queenswarm",
};

const PLUGINS: { name: string; status: string; cls: string }[] = [
  {
    name: "YouTube scouts",
    status: "Mock ingest until YOUTUBE_API_KEY is hydrated on the VPS.",
    cls: "text-pollen shadow-[0_0_38px_rgba(255,184,0,0.42)] border-pollen/40",
  },
  {
    name: "Slack nectar reporter",
    status: "Wire SLACK_WEBHOOK_URL in env-backed settings for Reporter bees.",
    cls: "text-data border-cyan/35 shadow-[0_0_38px_rgba(0,255,255,0.25)]",
  },
  {
    name: "Neo4j dance graph",
    status: "Online via Neo4j community container bolt://neo4j:7687 in Compose.",
    cls: "text-success border-success/40 shadow-[0_0_32px_rgba(0,255,136,0.25)]",
  },
  {
    name: "Chroma recipe recall",
    status: "Vector lane at chromadb:8000 powering semantic recipe search.",
    cls: "text-alert border-alert/40 shadow-[0_0_32px_rgba(255,0,170,0.35)]",
  },
  {
    name: "Redis waggle buses",
    status: "Pub/sub swarm_events plus sliding-window throttle counters.",
    cls: "text-danger border-danger/40 shadow-[0_0_32px_rgba(255,51,102,0.35)]",
  },
];

export default function PluginsPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-4xl font-semibold text-pollen">
          pollinized plugins
        </h1>
        <p className="mt-3 max-w-3xl font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Each bee snaps into deterministic rails · mocks preserve end-to-end flow while external keys hydrate on the conductor
          plane.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {PLUGINS.map((p) => (
          <article key={p.name} className={`rounded-3xl bg-black/35 p-5 ${p.cls} border`}>
            <p className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold tracking-tight">{p.name}</p>
            <p className="mt-4 font-[family-name:var(--font-jetbrains-mono)] text-sm text-muted-foreground">{p.status}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
