import { redirect } from "next/navigation";

import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";

export default function HiveHomePage() {
  if (OPERATOR_CONTROL_PLANE_ENABLED) {
    redirect("/agentic-os");
  }
  redirect("/dashboard");
}
