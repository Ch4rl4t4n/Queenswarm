import { Skeleton } from "@/components/ui/skeleton";

/** Route segment loading — External projects cockpit skeleton. */
export default function ExternalProjectsLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-12 w-full max-w-xl" />
      <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        <Skeleton className="h-[520px] w-full rounded-[22px]" />
        <div className="space-y-4">
          <Skeleton className="h-48 w-full rounded-[22px]" />
          <Skeleton className="h-64 w-full rounded-[22px]" />
        </div>
      </div>
    </div>
  );
}
