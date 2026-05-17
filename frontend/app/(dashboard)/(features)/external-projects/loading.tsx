import { Skeleton } from "@/components/ui/skeleton";

/** Route segment loading — External projects cockpit skeleton. */
export default function ExternalProjectsLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-12 w-full max-w-xl" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Skeleton className="h-[520px] w-full rounded-[22px]" />
        <div className="space-y-4">
          <Skeleton className="h-48 w-full rounded-[22px]" />
          <Skeleton className="h-64 w-full rounded-[22px]" />
        </div>
      </div>
    </div>
  );
}
