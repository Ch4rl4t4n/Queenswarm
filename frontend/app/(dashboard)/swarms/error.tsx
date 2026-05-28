"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function SwarmsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Swarms" error={error} reset={reset} />;
}
