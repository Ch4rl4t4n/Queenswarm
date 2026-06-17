import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { VerifyFirstPage } from "@/components/marketing/marketing-static-pages";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { isMarketingSiteRequest, marketingPublicOrigin } from "@/lib/marketing-host";

export const metadata: Metadata = {
  title: "Verify-first · Let Agents Cook",
  description: "Verified outcomes, not marketing claims. Every listing earns its score before publish.",
};

export default async function VerifyFirstRoute(): Promise<JSX.Element> {
  const headerStore = await headers();
  const host = headerStore.get("host");
  const e2eMarketing = headerStore.get("x-e2e-marketing-site");
  if (!isMarketingSiteRequest(host, e2eMarketing)) {
    redirect(`${marketingPublicOrigin()}/verify-first`);
  }

  return (
    <MarketingShell>
      <VerifyFirstPage />
    </MarketingShell>
  );
}
