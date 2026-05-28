import { LegacyRouteRedirect } from "@/components/hive/legacy-route-redirect";

/**
 * Backward-compatible alias for historical supervisor sessions route variants.
 */
export default function AgentsSessionsAliasPage() {
  return <LegacyRouteRedirect target="/agents#sessions" label="Redirecting to Agents…" />;
}
