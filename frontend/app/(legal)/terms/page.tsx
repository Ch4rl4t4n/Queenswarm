import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service · Queenswarm",
  description: "Queenswarm hive operator terms of service.",
};

export default function TermsPage(): JSX.Element {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16 text-(--qs-text)">
      <p className="font-[family-name:var(--font-space-grotesk)] text-xs uppercase tracking-[0.2em] text-pollen">Legal</p>
      <h1 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold">Terms of Service</h1>
      <p className="mt-4 text-sm text-(--qs-text-2)">Effective date: May 2026 · Queenswarm hive operator platform</p>
      <div className="prose prose-invert mt-8 space-y-4 text-sm leading-relaxed text-(--qs-text-2)">
        <p>
          By accessing Queenswarm you agree to use the platform only for lawful automation workflows, to safeguard API keys and
          tenant credentials, and to comply with applicable data-protection laws for any personal data processed through your hive.
        </p>
        <p>
          The service is provided as-is during early access. Operators are responsible for reviewing simulated outputs before acting
          on production integrations. We may suspend accounts that abuse rate limits, attempt unauthorized access, or violate third-party
          provider terms.
        </p>
        <p>
          Contact your hive administrator for enterprise agreements, data processing addenda, or billing questions.
        </p>
      </div>
      <Link href="/login" className="qs-btn qs-btn--ghost qs-btn--sm mt-10 inline-flex">
        Back to login
      </Link>
    </main>
  );
}
