"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Dashboard" error={error} reset={reset} />;
}
