"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function JobsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Async workflow jobs" error={error} reset={reset} />;
}
