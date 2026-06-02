"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function RoutinesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Routines" error={error} reset={reset} />;
}
