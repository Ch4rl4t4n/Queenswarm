"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { usePlatform } from "@/components/hive/platform-context";

interface PlatformRouteGuardProps {
  children: ReactNode;
}

/** Redirect blocked routes to dashboard when active tenant profile disables them. */
export function PlatformRouteGuard({ children }: PlatformRouteGuardProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { loading, isPathAllowed } = usePlatform();

  useEffect(() => {
    if (loading) {
      return;
    }
    if (!isPathAllowed(pathname)) {
      router.replace("/");
    }
  }, [loading, pathname, isPathAllowed, router]);

  if (!loading && !isPathAllowed(pathname)) {
    return null;
  }

  return children;
}
