"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function ForagersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Foragers" error={error} reset={reset} />;
}
