import { Skeleton } from "@/components/ui/skeleton";

/** Route segment skeleton for HiveMind galaxy. */
export default function HiveMindLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-[560px] w-full rounded-[28px]" />
    </div>
  );
}
