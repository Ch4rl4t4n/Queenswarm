"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function MonitoringError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Monitoring" error={error} reset={reset} />;
}
