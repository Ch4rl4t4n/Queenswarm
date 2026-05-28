"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function TasksError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Tasks" error={error} reset={reset} />;
}
