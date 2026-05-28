import { LegacyRouteRedirect } from "@/components/hive/legacy-route-redirect";
import { LearningConsole } from "@/components/hive/learning-console";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export const dynamic = "force-dynamic";

/** Learning engine cockpit — pollen, imitation exemplars, reflections. */
export default function LearningPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    return <LegacyRouteRedirect target="/knowledge#recipes" label="Redirecting to Knowledge…" />;
  }
  return <LearningConsole />;
}
