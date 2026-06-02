"use client";

import { MicIcon, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

interface OperatorShellFabProps {
  hidden?: boolean;
}

/** Mobile/tablet: primary FAB → new supervisor session (OW3). Desktop: Ballroom quick-open. */
export function OperatorShellFab({ hidden = false }: OperatorShellFabProps = {}): JSX.Element | null {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || hidden) {
    return null;
  }

  if (pathname.startsWith("/ballroom")) {
    return null;
  }

  return createPortal(
    <>
      <div className="fab-session-shell lg:hidden" data-testid="session-fab">
        <Link href="/agents#sessions" className="fab-session pointer-events-auto text-sm" title="New supervisor session">
          <Plus className="h-4 w-4 shrink-0" aria-hidden />
          <span>New session</span>
        </Link>
      </div>
      <div className="fab-ballroom-shell hidden lg:block" data-testid="ballroom-fab">
        <Link href="/ballroom" className="fab-ballroom pointer-events-auto text-sm" title="Open Ballroom">
          <MicIcon className="h-4 w-4 shrink-0" aria-hidden />
          <span>Open Ballroom</span>
        </Link>
      </div>
    </>,
    document.body,
  );
}
