"use client";

import { MicIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

/** Global quick-open Ballroom action (mobile + desktop). */
export function BallroomFab(): JSX.Element | null {
  const pathname = usePathname();
  const hidden = pathname.startsWith("/ballroom");
  if (hidden) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed bottom-[calc(5.4rem+env(safe-area-inset-bottom))] right-4 z-40 lg:bottom-6 lg:right-6">
      <Link
        href="/ballroom"
        className={cn(
          "pointer-events-auto inline-flex min-h-[48px] items-center gap-2 rounded-full border border-pollen/45 bg-[#0d121d]/95 px-4 py-2 text-sm font-semibold text-pollen shadow-[0_0_30px_rgb(255_184_0/0.3)] backdrop-blur transition",
          "hover:border-pollen/65 hover:bg-[#131a29]/95 hover:shadow-[0_0_34px_rgb(255_184_0/0.38)]",
        )}
        title="Open Ballroom (Alt+B)"
      >
        <MicIcon className="h-4 w-4" aria-hidden />
        <span className="hidden sm:inline">Open Ballroom</span>
        <span className="inline sm:hidden">Ballroom</span>
      </Link>
    </div>
  );
}
