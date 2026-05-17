export default function ConnectorsLoading() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-8">
      <div className="h-11 w-full max-w-md animate-pulse rounded-xl bg-black/55" aria-hidden />
      <div className="h-[260px] w-full animate-pulse rounded-2xl border border-cyan/10 bg-black/55" aria-hidden />
    </main>
  );
}
