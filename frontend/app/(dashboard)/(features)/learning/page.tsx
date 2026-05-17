import { redirect } from "next/navigation";

import { LearningConsole } from "@/components/hive/learning-console";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export const dynamic = "force-dynamic";

/** Learning engine cockpit — pollen, imitation exemplars, reflections. */
export default function LearningPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect("/knowledge#recipes");
  }
  return <LearningConsole />;
}
