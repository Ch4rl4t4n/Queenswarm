import type { Metadata } from "next";

import { MarketingEvalPageClient } from "@/components/marketing/marketing-eval-page-client";
import { MarketingShell } from "@/components/marketing/marketing-shell";

export const metadata: Metadata = {
  title: "Free workflow eval · Let Agents Cook",
  description:
    "Paste SKILL.md or agent workflow markdown — get a simulate-first EVAL_REPORT with PASS/FAIL before you list on Gumroad.",
};

export default function MarketingEvalPage(): JSX.Element {
  return (
    <MarketingShell>
      <MarketingEvalPageClient />
    </MarketingShell>
  );
}
