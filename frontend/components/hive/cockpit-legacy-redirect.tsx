"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Preserves hash + query when migrating bookmarks from `/cockpit` → `/agentic-os`. */
export function CockpitLegacyRedirect() {
  const router = useRouter();

  useEffect(() => {
    const { search, hash } = window.location;
    router.replace(`/agentic-os${search}${hash}`);
  }, [router]);

  return <p className="text-sm text-(--qs-muted)">Redirecting to Agentic OS…</p>;
}
