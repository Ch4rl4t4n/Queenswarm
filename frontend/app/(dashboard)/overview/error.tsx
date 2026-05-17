"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function OverviewError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Overview" error={error} reset={reset} />;
}
