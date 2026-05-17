interface SectionRouteLoadingProps {
  readonly title: string;
}

export function SectionRouteLoading({ title }: SectionRouteLoadingProps): JSX.Element {
  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <div className="h-10 w-56 animate-pulse rounded-lg bg-zinc-900/80" />
        <div className="h-4 w-md max-w-full animate-pulse rounded bg-zinc-900/60" />
      </div>
      <div className="rounded-2xl border border-cyan/10 bg-[#070d17]/50 p-4">
        <div className="h-4 w-64 max-w-full animate-pulse rounded bg-zinc-900/70" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }, (_, index) => (
          <div
            key={`${title}-loading-card-${index}`}
            className="h-28 animate-pulse rounded-2xl border border-zinc-800/80 bg-zinc-950/70"
          />
        ))}
      </div>
    </div>
  );
}
