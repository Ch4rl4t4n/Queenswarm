import { redirect } from "next/navigation";

import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hubFallbackTarget } from "@/lib/hive-navigation-mode";

export default function OverviewPage(): JSX.Element {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(hubFallbackTarget("overview"));
  }
  redirect("/");
}
