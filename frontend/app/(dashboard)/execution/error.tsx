"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function ExecutionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Execution" error={error} reset={reset} />;
}
