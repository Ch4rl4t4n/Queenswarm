import { MonitoringSkeleton } from "@/components/monitoring/monitoring-skeleton";

export default function MonitoringLoading() {
  return (
    <div className="space-y-8">
      <div className="h-10 w-64 animate-pulse rounded-lg bg-zinc-900/80" />
      <MonitoringSkeleton />
    </div>
  );
}
