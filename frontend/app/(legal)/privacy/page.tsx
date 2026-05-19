import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy · Queenswarm",
  description: "Queenswarm privacy policy for hive operators.",
};

export default function PrivacyPage(): JSX.Element {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16 text-(--qs-text)">
      <p className="font-[family-name:var(--font-space-grotesk)] text-xs uppercase tracking-[0.2em] text-pollen">Legal</p>
      <h1 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold">Privacy Policy</h1>
      <p className="mt-4 text-sm text-(--qs-text-2)">Effective date: May 2026 · Queenswarm hive operator platform</p>
      <div className="prose prose-invert mt-8 space-y-4 text-sm leading-relaxed text-(--qs-text-2)">
        <p>
          Queenswarm stores operator account data (email, profile preferences, audit logs) and workflow artefacts required to run your
          agent swarms. Secrets such as API keys and TOTP material are encrypted at rest where configured and are never sent to LLM
          providers as part of routine prompts.
        </p>
        <p>
          We use structured logging for security and reliability. Logs may include anonymized request metadata and hashed identifiers;
          raw passwords and one-time codes are not logged. Retention defaults follow tenant audit settings (typically 60 days for admin
          actions).
        </p>
        <p>
          To request export or deletion of operator account data, contact your hive administrator or email the address published on
          queenswarm.love.
        </p>
      </div>
      <Link href="/login" className="qs-btn qs-btn--ghost qs-btn--sm mt-10 inline-flex">
        Back to login
      </Link>
    </main>
  );
}
