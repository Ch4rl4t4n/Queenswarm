export default function BallroomLoading(): JSX.Element {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-8">
      <div className="h-10 w-full max-w-md animate-pulse rounded-xl bg-zinc-900/70" aria-hidden />
      <div className="h-4 w-full max-w-xl animate-pulse rounded bg-zinc-900/50" aria-hidden />
      <div className="min-h-[320px] w-full animate-pulse rounded-2xl border border-cyan/15 bg-[#070d17]/60 shadow-[0_0_40px_rgb(0_255_255/0.08)]" aria-hidden />
    </main>
  );
}
