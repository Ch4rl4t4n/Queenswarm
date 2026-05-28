"use client";

import { SectionRouteError } from "@/components/hive/section-route-error";

export default function SettingsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  return <SectionRouteError title="Settings" error={error} reset={reset} />;
}
