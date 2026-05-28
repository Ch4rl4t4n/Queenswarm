import { LegacyRouteRedirect } from "@/components/hive/legacy-route-redirect";

/**
 * Backward-compatible alias for historical hierarchy deep-links under /agents.
 */
export default function AgentsHierarchyAliasPage() {
  return <LegacyRouteRedirect target="/agents#hierarchy" label="Redirecting to Agents…" />;
}
