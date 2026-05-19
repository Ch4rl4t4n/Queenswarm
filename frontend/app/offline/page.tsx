import Link from "next/link";

/** Minimal offline fallback — served by service worker when navigation fails. */
export default function OfflinePage(): JSX.Element {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-[#07030f] px-6 py-12 text-center text-[#fafafa]">
      <div className="hive-hex mb-6 flex h-16 w-16 items-center justify-center border-[6px] border-black/55 bg-gradient-to-br from-pollen to-amber-600 shadow-[0_0_28px_rgb(255_184_0/0.45)] ring-[6px] ring-black/70">
        <span className="text-lg font-black text-black">Q</span>
      </div>
      <h1 className="font-[family-name:var(--font-poppins)] text-2xl font-semibold text-pollen">
        Hive offline
      </h1>
      <p className="mt-3 max-w-sm font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
        No network — showing cached shell. Reconnect to sync agents and verified simulations.
      </p>
      <Link
        href="/login"
        className="mt-8 inline-flex min-h-11 items-center rounded-xl border border-cyan/30 bg-black/50 px-6 py-2 font-[family-name:var(--font-poppins)] text-sm text-cyan hover:border-cyan/60 touch-manipulation"
      >
        Back to login
      </Link>
    </div>
  );
}
