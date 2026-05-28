"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function AgenticOsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Agentic OS" error={error} reset={reset} />;
}
