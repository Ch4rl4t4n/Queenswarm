"use client";

import { BellIcon } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { toast } from "sonner";

import type { DashboardSummary } from "@/lib/hive-types";
import { hiveMobileRouteMeta } from "@/lib/hive-mobile-meta";
import { cn } from "@/lib/utils";

interface HiveMobileHeaderProps {
  pathname: string;
  summary: DashboardSummary | null;
  className?: string;
}

function onlineLine(summary: DashboardSummary | null): string {
  if (!summary?.agents?.by_status) {
    return "syncing hive…";
  }
  const total = summary.agents.total;
  let offlineErr = 0;
  for (const [k, v] of Object.entries(summary.agents.by_status)) {
    const u = k.toUpperCase();
    if (u === "OFFLINE" || u === "ERROR") offlineErr += v;
  }
  const online = Math.max(0, total - offlineErr);
  return total ? `${online} agentov online` : "hive warming…";
}

/** Mobile-first sticky strip. */
export function HiveMobileHeader({ pathname, summary, className }: HiveMobileHeaderProps) {
  const meta = useMemo(() => hiveMobileRouteMeta(pathname), [pathname]);
  const contextualLine = useMemo(() => {
    if (pathname === "/") {
      return onlineLine(summary);
    }
    if (pathname.startsWith("/ballroom") || pathname === "/ballroom") {
      return "Voice + transcript";
    }
    return meta.staticSubtitle ?? "";
  }, [pathname, summary, meta.staticSubtitle]);

  return (
    <header
      className={cn(
        "sticky top-0 z-[45] flex items-start justify-between gap-3 border-b border-cyan/[0.12] bg-[#0a0a0c]/95 px-4 py-4 backdrop-blur-lg lg:hidden",
        /** Clear iOS notch */
        "pt-[calc(1rem+env(safe-area-inset-top,0px))]",
        className,
      )}
    >
      <Link href="/" className="flex min-w-0 flex-1 items-start gap-3" prefetch aria-label="Go to dashboard">
        <span className="hive-hex mt-1 flex h-10 w-10 shrink-0 items-center justify-center border-[5px] border-black/55 bg-gradient-to-br from-pollen to-amber-600 shadow-[0_0_22px_rgb(255_184_0/0.52)] ring-[5px] ring-black/70">
          <span className="text-xs font-black text-black">Q</span>
        </span>
        <span className="min-w-0">
          <p className="font-[family-name:var(--font-poppins)] text-[11px] font-semibold uppercase tracking-[0.18em] text-pollen">{meta.kicker}</p>
          <p className="line-clamp-2 font-[family-name:var(--font-inter)] text-xs text-muted-foreground">{contextualLine}</p>
        </span>
      </Link>
      <button
        type="button"
        aria-label="Notifications"
        className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan/[0.18] bg-black/55 text-zinc-300 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.05)] hover:border-pollen/35 hover:text-pollen"
        onClick={() => toast.message("Hive alerts", { description: "Žiadne neprečítané." })}
      >
        <BellIcon className="h-[18px] w-[18px]" aria-hidden />
      </button>
    </header>
  );
}
