"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function IntegrationsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Integrations" error={error} reset={reset} />;
}
