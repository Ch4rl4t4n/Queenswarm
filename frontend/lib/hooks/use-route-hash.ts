"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/** Current location hash (client-only) — updates on hashchange and pathname changes. */
export function useRouteHash(): string {
  const pathname = usePathname();
  const [hash, setHash] = useState("");

  useEffect(() => {
    const read = (): void => setHash(window.location.hash);
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, [pathname]);

  return hash;
}
