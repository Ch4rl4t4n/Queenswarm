"use client";

import { Suspense } from "react";

import { LazyOperatorCockpitPanel } from "@/components/hive/operator-cockpit-panel";

export default function CockpitPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 lg:p-6">
      <Suspense
        fallback={
          <p className="text-sm text-(--qs-muted)">Loading Hive Cockpit…</p>
        }
      >
        <LazyOperatorCockpitPanel />
      </Suspense>
    </div>
  );
}
