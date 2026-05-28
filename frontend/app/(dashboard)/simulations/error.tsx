"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function SimulationsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Simulations" error={error} reset={reset} />;
}
