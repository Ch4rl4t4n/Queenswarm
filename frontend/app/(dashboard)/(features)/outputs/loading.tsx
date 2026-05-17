import { Skeleton } from "@/components/ui/skeleton";

/** Route segment loading — Outputs grid skeleton. */
export default function OutputsLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-full max-w-xl" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-52 w-full rounded-[22px]" />
        ))}
      </div>
    </div>
  );
}
