import type { Metadata } from "next";

interface ProofPageProps {
  params: Promise<{ token: string }>;
}

interface ProofPublicReceipt {
  valid: boolean;
  domain: string;
  artifact_type?: string;
  title?: string;
  trust_lane?: string;
  verified_at?: string;
  event_kind?: string;
  message: string;
}

async function fetchProof(token: string): Promise<ProofPublicReceipt> {
  const origin = process.env.NEXT_PUBLIC_API_ORIGIN || "https://queenswarm.love";
  const res = await fetch(`${origin}/api/v1/public/proof/${encodeURIComponent(token)}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) {
    return { valid: false, domain: origin, message: "Receipt unavailable." };
  }
  return (await res.json()) as ProofPublicReceipt;
}

export async function generateMetadata({ params }: ProofPageProps): Promise<Metadata> {
  const { token } = await params;
  const proof = await fetchProof(token);
  const title = proof.valid ? `Proof · ${proof.title ?? "Verified"}` : "Proof-of-Hive";
  return { title: `${title} · Queenswarm` };
}

export default async function ProofPage({ params }: ProofPageProps) {
  const { token } = await params;
  const proof = await fetchProof(token);

  return (
    <main className="min-h-screen bg-[#050510] px-4 py-16 text-[#e8e8f0]">
      <div className="mx-auto max-w-lg rounded-xl border border-[#FFB80033] bg-black/40 p-6 shadow-[0_0_24px_#FFB80022]">
        <p className="font-mono text-xs uppercase tracking-widest text-[#00FFFF]">Proof-of-Hive</p>
        <h1 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-2xl font-bold text-[#FFB800]">
          {proof.valid ? "Verified receipt" : "Invalid receipt"}
        </h1>
        {proof.valid ? (
          <dl className="mt-6 space-y-3 text-sm">
            <div>
              <dt className="text-[#8888aa]">Artifact</dt>
              <dd className="font-medium">{proof.title ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#8888aa]">Type</dt>
              <dd>{proof.artifact_type ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#8888aa]">Trust lane</dt>
              <dd className="font-mono text-[#00FF88]">{proof.trust_lane ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#8888aa]">Verified at</dt>
              <dd className="font-mono text-xs">{proof.verified_at ?? "—"}</dd>
            </div>
            {proof.event_kind ? (
              <div>
                <dt className="text-[#8888aa]">Event</dt>
                <dd>{proof.event_kind}</dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p className="mt-4 text-sm text-[#FF3366]">{proof.message}</p>
        )}
        <p className="mt-8 text-xs text-[#8888aa]">{proof.message}</p>
        <p className="mt-2 font-mono text-[10px] text-[#555577] break-all">{token.slice(0, 48)}…</p>
      </div>
    </main>
  );
}
