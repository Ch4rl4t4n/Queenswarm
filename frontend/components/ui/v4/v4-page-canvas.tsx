import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4PageCanvasProps extends ComponentPropsWithoutRef<"div"> {
  children: ReactNode;
}

/** Shared V4 page stack — same max-width and vertical rhythm as Queen Dashboard. */
export function V4PageCanvas({ children, className, ...rest }: V4PageCanvasProps) {
  return (
    <div className={cn("v4-page-canvas flex w-full flex-col gap-8", className)} {...rest}>
      {children}
    </div>
  );
}
