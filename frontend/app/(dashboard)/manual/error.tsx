"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function ManualError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Manual" error={error} reset={reset} />;
}
