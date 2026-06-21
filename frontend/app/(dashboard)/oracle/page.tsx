import { LegacyRouteRedirect } from "@/components/hive/legacy-route-redirect";

/**
 * Legacy route — Oracle removed; priorities live on Agentic OS overview.
 * Client redirect preserves any `#hash` from old bookmarks (a server 307 drops
 * the fragment).
 */
export default function OraclePage() {
  return (
    <LegacyRouteRedirect
      target="/agentic-os"
      preserveIncomingHash
      label="Redirecting to Agentic OS…"
    />
  );
}
