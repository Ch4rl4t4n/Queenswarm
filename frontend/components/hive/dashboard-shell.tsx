"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import { HiveTopBar } from "@/components/hive/hive-top-bar";
import type { DashboardOperatorMe } from "@/lib/hive-dashboard-session";
import type { DashboardSummary } from "@/lib/hive-types";

interface DashboardShellProps {
  children: ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname();
  const [session, setSession] = useState<DashboardOperatorMe | null>(null);
  const fallbackEmail = "operator@queenswarm.love";
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/api/proxy/auth/me", { credentials: "include" });
        if (!res.ok) {
          return;
        }
        const body = (await res.json()) as DashboardOperatorMe;
        if (alive && typeof body.email === "string") {
          setSession(body);
        }
      } catch {
        /* offline */
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

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
        {/* Hex field + vignette */}
        <div aria-hidden className="pointer-events-none fixed inset-y-0 right-0 -z-[1] hive-bg-pattern opacity-[0.72] lg:left-16" />
        <div
          aria-hidden
          className="pointer-events-none fixed inset-y-0 right-0 -z-[1] bg-[radial-gradient(ellipse_at_50%_-10%,rgba(255,184,0,0.07),transparent_55%)] lg:left-16"
        />

        <HiveMobileHeader pathname={pathname} summary={summary} />

        <div className="hidden lg:block">
          <HiveTopBar email={session?.email ?? fallbackEmail} displayName={session?.display_name} />
        </div>

        <main className="relative mx-auto w-full max-w-[1400px] flex-1 px-4 pb-[calc(7rem+env(safe-area-inset-bottom))] pt-4 md:pb-20 md:pt-6 lg:px-8 lg:pb-16">
          {children}
        </main>

        <footer className="hidden border-t border-cyan/10 py-6 text-center font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-cyan/45 lg:block">
          QueenSwarm · verified simulations · global sync · rapid loop
        </footer>

        <HiveBottomNav onMore={() => setMoreOpen(true)} />
        <HiveMoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
      </div>
    </div>
  );
}
