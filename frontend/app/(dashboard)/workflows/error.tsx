"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function WorkflowsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Workflows" error={error} reset={reset} />;
}
