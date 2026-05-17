export function MonitoringSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-4 w-48 rounded bg-zinc-800" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-2xl bg-zinc-900/80" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-[300px] rounded-2xl bg-zinc-900/80" />
        <div className="h-[300px] rounded-2xl bg-zinc-900/80" />
      </div>
    </div>
  );
}
