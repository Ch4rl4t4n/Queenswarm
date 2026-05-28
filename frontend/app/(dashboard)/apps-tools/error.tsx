"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function AppsToolsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Apps & Tools" error={error} reset={reset} />;
}
