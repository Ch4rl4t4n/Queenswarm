"use client";

import { MicIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

/** Global quick-open Ballroom action (mobile + desktop). */
export function BallroomFab(): JSX.Element | null {
  const pathname = usePathname();
  const hidden = pathname.startsWith("/ballroom");
  if (hidden) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed bottom-[calc(5.4rem+env(safe-area-inset-bottom))] right-4 z-40 lg:hidden">
      <Link href="/ballroom" className="fab-ballroom pointer-events-auto text-sm" title="Open Ballroom (Alt+B)">
        <MicIcon className="h-4 w-4" aria-hidden />
        <span className="hidden sm:inline">Open Ballroom</span>
        <span className="inline sm:hidden">Ballroom</span>
      </Link>
    </div>
  );
}
