"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function AgentsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Agents" error={error} reset={reset} />;
}
