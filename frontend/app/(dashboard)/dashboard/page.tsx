import { redirect } from "next/navigation";

import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export default function DashboardHubPage(): JSX.Element {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect("/");
  }
  redirect("/");
}
