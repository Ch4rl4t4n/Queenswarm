import { redirect } from "next/navigation";

import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export default function ExecutionPage(): JSX.Element {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect("/tasks");
  }
  redirect("/tasks");
}
