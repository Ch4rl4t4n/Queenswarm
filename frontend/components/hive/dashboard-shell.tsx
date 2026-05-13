"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import type { DashboardSummary } from "@/lib/hive-types";

interface DashboardShellProps {
  children: ReactNode;
}

const SIDEBAR_W = "lg:left-[220px]";

/** Desktop cockpit: fixed left sidebar only — no duplicated top horizontal route nav. */
export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/api/proxy/dashboard/summary", { credentials: "include" });
        if (!res.ok) {
          return;
        }
        const body = (await res.json()) as DashboardSummary;
        if (alive) {
          setSummary(body);
        }
      } catch {
        /* offline */
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="relative flex min-h-screen bg-hive-bg text-[#fafafa]">
      <HiveSidebar pathname={pathname} />

      <div className="relative flex min-h-[100dvh] flex-1 flex-col">
        {/* Hex field + vignette — offset aligned to 220px desktop sidebar */}
        <div
          aria-hidden
          className={`pointer-events-none fixed inset-y-0 right-0 -z-[1] hive-bg-pattern opacity-[0.72] ${SIDEBAR_W}`}
        />
        <div
          aria-hidden
          className={`pointer-events-none fixed inset-y-0 right-0 -z-[1] bg-[radial-gradient(ellipse_at_50%_-10%,rgba(255,184,0,0.07),transparent_55%)] ${SIDEBAR_W}`}
        />

        <HiveMobileHeader pathname={pathname} summary={summary} />

        <main className="relative mx-auto w-full max-w-[1400px] flex-1 px-4 pb-[calc(7rem+env(safe-area-inset-bottom))] pt-8 md:pb-20 lg:px-9 lg:pb-16">
          {children}
        </main>

        <footer className="hidden border-t border-cyan/10 py-6 text-center font-[family-name:var(--font-poppins)] text-[10px] text-cyan/45 lg:block">
          QueenSwarm · cockpit + ballroom
        </footer>

        <HiveBottomNav onMore={() => setMoreOpen(true)} />
        <HiveMoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
      </div>
    </div>
  );
}
