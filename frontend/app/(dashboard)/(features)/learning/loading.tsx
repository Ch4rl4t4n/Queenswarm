export default function LearningLoading() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-8">
      <div className="h-11 w-full max-w-md animate-pulse rounded-xl bg-black/55" aria-hidden />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="min-h-[200px] animate-pulse rounded-2xl border border-cyan/10 bg-black/55" aria-hidden />
        <div className="min-h-[200px] animate-pulse rounded-2xl border border-cyan/10 bg-black/55" aria-hidden />
      </div>
    </main>
  );
}
