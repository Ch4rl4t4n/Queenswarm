import { Suspense } from "react";

import { CockpitPageClient } from "@/components/hive/cockpit-page-client";
import { HivePageShellSkeleton } from "@/components/hive/hive-page-shell-skeleton";

export default function AgenticOsPage() {
  return (
    <Suspense fallback={<HivePageShellSkeleton withSubnav />}>
      <CockpitPageClient />
    </Suspense>
  );
}
