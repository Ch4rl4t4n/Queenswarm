import { Skeleton } from "@/components/ui/skeleton";

export default function SwarmsLoading() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}
