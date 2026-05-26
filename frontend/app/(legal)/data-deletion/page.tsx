import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Data Deletion · Queenswarm",
  description: "How to request deletion of your Queenswarm operator account data.",
};

export default function DataDeletionPage(): JSX.Element {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16 text-(--qs-text)">
      <p className="font-[family-name:var(--font-space-grotesk)] text-xs uppercase tracking-[0.2em] text-pollen">Legal</p>
      <h1 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold">Data deletion</h1>
      <p className="mt-4 text-sm text-(--qs-text-2)">Queenswarm · operator account and connected integrations</p>
      <div className="prose prose-invert mt-8 space-y-4 text-sm leading-relaxed text-(--qs-text-2)">
        <p>
          To delete your Queenswarm operator account and associated workflow data, email{" "}
          <a href="mailto:admin@queenswarm.love" className="text-cyan underline">
            admin@queenswarm.love
          </a>{" "}
          from the address linked to your account. We confirm identity, then remove profile data, audit logs tied to your
          user id, and OAuth tokens stored for social connectors within 30 days unless retention is required by law.
        </p>
        <p>
          To revoke Meta (Instagram/Facebook) access only: Meta → Settings → Business integrations → remove the Queenswarm
          app, or use Facebook Login → Apps and websites in your personal Meta account settings.
        </p>
      </div>
      <Link href="/privacy" className="qs-btn qs-btn--ghost qs-btn--sm mt-10 inline-flex">
        Privacy policy
      </Link>
    </main>
  );
}
