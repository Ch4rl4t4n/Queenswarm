import { Skeleton } from "@/components/ui/skeleton";

export default function RootLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-40 w-full" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  );
}
