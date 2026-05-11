import { Skeleton } from "@/components/ui/skeleton";

export default function WorkflowsLoading() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 10 }).map((_, i) => (
        <Skeleton key={i} className="h-24 w-full" />
      ))}
    </div>
  );
}
