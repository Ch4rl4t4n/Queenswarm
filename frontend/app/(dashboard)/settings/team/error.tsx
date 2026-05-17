"use client";

export default function TeamSettingsError({ error }: { error: Error }) {
  return (
    <div className="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-5">
      <p className="text-sm text-rose-200">Unable to render team settings: {error.message}</p>
    </div>
  );
}
