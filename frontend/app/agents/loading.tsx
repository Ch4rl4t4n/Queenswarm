import { Skeleton } from "@/components/ui/skeleton";

export default function AgentsLoading() {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 12 }).map((_, i) => (
        <Skeleton key={i} className="aspect-[120/140] hive-hex" />
      ))}
    </div>
  );
}
