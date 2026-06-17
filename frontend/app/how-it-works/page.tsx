import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { HowItWorksPage } from "@/components/marketing/marketing-static-pages";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { isMarketingSiteRequest, marketingPublicOrigin } from "@/lib/marketing-host";

export const metadata: Metadata = {
  title: "How it works · Let Agents Cook",
  description: "Browse verified skills, buy on Gumroad, download the bundle, run simulate-first in your stack.",
};

export default async function HowItWorksRoute(): Promise<JSX.Element> {
  const headerStore = await headers();
  const host = headerStore.get("host");
  const e2eMarketing = headerStore.get("x-e2e-marketing-site");
  if (!isMarketingSiteRequest(host, e2eMarketing)) {
    redirect(`${marketingPublicOrigin()}/how-it-works`);
  }

  return (
    <MarketingShell>
      <HowItWorksPage />
    </MarketingShell>
  );
}
