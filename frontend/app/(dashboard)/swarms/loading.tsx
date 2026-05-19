export default function SwarmsLoading() {
  return (
    <div className="space-y-6">
      <div className="h-24 animate-pulse rounded-[var(--qs-radius-lg)] bg-white/5" />
      <div className="v4-stat-grid">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="v4-stat h-[120px] animate-pulse bg-white/5" />
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-[var(--qs-radius-lg)] bg-white/5" />
      <div className="v4-cols-2">
        <div className="h-64 animate-pulse rounded-[var(--qs-radius-lg)] bg-white/5" />
        <div className="h-64 animate-pulse rounded-[var(--qs-radius-lg)] bg-white/5" />
      </div>
    </div>
  );
}
