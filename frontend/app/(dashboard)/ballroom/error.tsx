"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function BallroomError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Ballroom" error={error} reset={reset} />;
}
