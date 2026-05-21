import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { resolveInternalBackendOrigin } from "@/lib/backend-origin";
import type { LeadMagnetLandingResponse } from "@/lib/hive-types";

interface MagnetPageProps {
  params: Promise<{ templateId: string }>;
}

async function fetchLanding(templateId: string): Promise<LeadMagnetLandingResponse | null> {
  const origin = resolveInternalBackendOrigin();
  try {
    const res = await fetch(`${origin}/api/v1/marketing/lead-magnets/${encodeURIComponent(templateId)}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as LeadMagnetLandingResponse;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: MagnetPageProps): Promise<Metadata> {
  const { templateId } = await params;
  const landing = await fetchLanding(templateId);
  if (!landing) {
    return { title: "Lead magnet · Queenswarm" };
  }
  return {
    title: `${landing.headline} · Queenswarm`,
    description: landing.tagline,
  };
}

export default async function MagnetLandingPage({ params }: MagnetPageProps): Promise<JSX.Element> {
  const { templateId } = await params;
  const landing = await fetchLanding(templateId);
  if (!landing) {
    notFound();
  }

  const wizardPath = landing.cta_url.replace(/^https:\/\/[^/]+/, "");

  return (
    <main className="min-h-screen bg-[#050510] px-4 py-16 text-(--qs-text)">
      <div className="mx-auto max-w-2xl">
        <p className="font-[family-name:var(--font-space-grotesk)] text-xs uppercase tracking-[0.2em] text-pollen">
          Queenswarm · verified agent swarm
        </p>
        <h1
          className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold leading-tight md:text-4xl"
          style={{ textShadow: `0 0 32px ${landing.accent_hex}66` }}
        >
          {landing.headline}
        </h1>
        <p className="mt-4 text-base text-(--qs-text-2)">{landing.tagline}</p>
        <p className="mt-2 text-sm text-(--qs-text-3)">{landing.description}</p>

        <ul className="mt-8 space-y-3 text-sm text-(--qs-text-2)">
          {landing.bullets.map((bullet) => (
            <li key={bullet} className="flex gap-2">
              <span className="text-cyan" aria-hidden>
                ✓
              </span>
              {bullet}
            </li>
          ))}
        </ul>

        <dl className="mt-8 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3">
            <dt className="text-[10px] uppercase text-(--qs-text-3)">Setup</dt>
            <dd className="mt-1 font-mono text-lg text-pollen">{landing.estimated_minutes} min</dd>
          </div>
          <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3">
            <dt className="text-[10px] uppercase text-(--qs-text-3)">Bees</dt>
            <dd className="mt-1 font-mono text-lg text-cyan">{landing.agent_count}</dd>
          </div>
          <div className="rounded-xl border border-(--qs-border) bg-white/5 p-3">
            <dt className="text-[10px] uppercase text-(--qs-text-3)">Saved</dt>
            <dd className="mt-1 font-mono text-lg text-(--qs-green)">~{landing.time_saved_hours_per_week}h/wk</dd>
          </div>
        </dl>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href={wizardPath} className="qs-btn qs-btn--primary">
            {landing.cta_label}
          </Link>
          <Link href="/login" className="qs-btn qs-btn--ghost">
            Login to hive
          </Link>
        </div>
      </div>
    </main>
  );
}
