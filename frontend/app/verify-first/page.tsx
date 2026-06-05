import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { VerifyFirstPage } from "@/components/marketing/marketing-static-pages";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { isMarketingHost, marketingPublicOrigin } from "@/lib/marketing-host";

export const metadata: Metadata = {
  title: "Verify-first · Let Agents Cook",
  description: "Verified outcomes, not marketing claims. Every listing earns its score before publish.",
};

export default async function VerifyFirstRoute(): Promise<JSX.Element> {
  const host = (await headers()).get("host");
  if (!isMarketingHost(host)) {
    redirect(`${marketingPublicOrigin()}/verify-first`);
  }

  return (
    <MarketingShell>
      <VerifyFirstPage />
    </MarketingShell>
  );
}
