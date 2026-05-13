"use client";

export default function GlobalErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto mt-24 max-w-xl rounded-3xl border border-danger bg-black/55 p-8 text-danger shadow-[0_0_42px_rgba(255,51,102,0.35)]">
      <p className="font-[family-name:var(--font-poppins)] text-2xl font-semibold tracking-tight text-pollen">
        hive anomaly
      </p>
      <p className="mt-4 font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">{error.message}</p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-6 rounded-full border border-pollen px-4 py-2 font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.3em] text-pollen"
      >
        reset comb
      </button>
    </div>
  );
}
