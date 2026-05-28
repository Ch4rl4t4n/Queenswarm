"use client";

import dynamic from "next/dynamic";

import { HivePageShellSkeleton } from "@/components/hive/hive-page-shell-skeleton";

const OperatorCockpitPanel = dynamic(
  () => import("@/components/hive/operator-cockpit-panel").then((mod) => ({ default: mod.OperatorCockpitPanel })),
  {
    ssr: false,
    loading: () => <HivePageShellSkeleton withSubnav />,
  },
);

/** Client shell — code-splits the heavy operator cockpit panel. */
export function CockpitPageClient() {
  return <OperatorCockpitPanel />;
}
