"use client";

import { MicIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

/** Global quick-open Ballroom action — visible on mobile, tablet, and desktop. */
export function BallroomFab(): JSX.Element | null {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || pathname.startsWith("/ballroom")) {
    return null;
  }

  return createPortal(
    <div className="fab-ballroom-shell" data-testid="ballroom-fab">
      <Link href="/ballroom" className="fab-ballroom pointer-events-auto text-sm" title="Open Ballroom (Ctrl+B)">
        <MicIcon className="h-4 w-4 shrink-0" aria-hidden />
        <span className="hidden sm:inline">Open Ballroom</span>
        <span className="inline sm:hidden">Ballroom</span>
      </Link>
    </div>,
    document.body,
  );
}
