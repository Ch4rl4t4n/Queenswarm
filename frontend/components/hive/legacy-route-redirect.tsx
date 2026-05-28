"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface LegacyRouteRedirectProps {
  /** Canonical destination — may include `?query` and `#hash`. */
  target: string;
  /** When true, keep the incoming hash if the target omits one. */
  preserveIncomingHash?: boolean;
  label?: string;
}

/**
 * Client redirect for legacy bookmarks — preserves `#hash` and `?query` that HTTP 307 cannot.
 *
 * Used by Phase 7.0 consolidated IA aliases (`/connectors` → `/integrations?tab=hub`, etc.).
 */
export function LegacyRouteRedirect({
  target,
  preserveIncomingHash = false,
  label = "Redirecting…",
}: LegacyRouteRedirectProps) {
  const router = useRouter();

  useEffect(() => {
    const incoming = window.location;
    const canonical = new URL(target, incoming.origin);
    let destination = `${canonical.pathname}${canonical.search}`;
    const hash = canonical.hash || (preserveIncomingHash ? incoming.hash : "");
    if (hash.length > 0) {
      destination += hash.startsWith("#") ? hash : `#${hash}`;
    }
    // Full navigation for hash/query legacy aliases — App Router client replace can drop hash in e2e.
    if (canonical.hash.length > 0 || canonical.search.length > 0 || preserveIncomingHash) {
      window.location.replace(destination);
      return;
    }
    router.replace(destination);
  }, [router, target, preserveIncomingHash]);

  return (
    <p className="text-sm text-(--qs-muted)" role="status">
      {label}
    </p>
  );
}
