import { cn } from "@/lib/utils";

export interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      role="presentation"
      className={cn("animate-pulse rounded-md bg-cyan/10 ring-1 ring-cyan/20", className)}
    />
  );
}
