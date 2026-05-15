"use client";

import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import type { DashboardSummary } from "@/lib/hive-types";

interface DashboardShellProps {
  children: ReactNode;
}

const SIDEBAR_W = "lg:left-[220px]";

/** Desktop power-user shortcuts (ignored when typing in inputs). */
function useDesktopHiveShortcuts(router: ReturnType<typeof useRouter>): void {
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    if (!mq.matches) {
      return undefined;
    }

    const go = (path: string) => {
      router.push(path);
      router.refresh();
    };

    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
        return;
      }
      if (!e.altKey || e.metaKey || e.ctrlKey) {
        return;
      }
      switch (e.key.toLowerCase()) {
        case "h":
          e.preventDefault();
          go("/overview");
          break;
        case "t":
          e.preventDefault();
          go("/execution");
          break;
        case "b":
          e.preventDefault();
          go("/ballroom");
          break;
        case "o":
          e.preventDefault();
          go("/knowledge");
          break;
        case "m":
          e.preventDefault();
          go("/integrations");
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);
}

/** Desktop cockpit + mobile-first drawer / sheets / bottom nav. */
export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  useDesktopHiveShortcuts(router);

  const closeDrawer = useCallback(() => setMobileDrawerOpen(false), []);

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

  useEffect(() => {
    closeDrawer();
  }, [pathname, closeDrawer]);

  return (
    <div className="relative flex min-h-screen bg-hive-bg text-[#fafafa]">
      <HiveSidebar pathname={pathname} mobileOpen={mobileDrawerOpen} onMobileClose={closeDrawer} />

      <div className="relative flex min-h-[100dvh] flex-1 flex-col">
        <div
          aria-hidden
          className={`pointer-events-none fixed inset-y-0 right-0 -z-[1] hive-bg-pattern opacity-[0.72] ${SIDEBAR_W}`}
        />
        <div
          aria-hidden
          className={`pointer-events-none fixed inset-y-0 right-0 -z-[1] bg-[radial-gradient(ellipse_at_50%_-10%,rgba(255,184,0,0.07),transparent_55%)] ${SIDEBAR_W}`}
        />

        <HiveMobileHeader pathname={pathname} summary={summary} onOpenNav={() => setMobileDrawerOpen(true)} />

        <main data-hive-shell="canvas" className="relative mx-auto w-full max-w-[1400px] flex-1 px-4 pb-[calc(7rem+env(safe-area-inset-bottom))] pt-8 md:pb-20 lg:px-9 lg:pb-16">
          {children}
        </main>

        <footer className="hidden border-t border-cyan/10 py-6 text-center font-[family-name:var(--font-poppins)] text-[10px] text-cyan/45 lg:block">
          QueenSwarm · consolidated cockpit · Alt+H overview · Alt+T execution · Alt+B ballroom · Alt+O knowledge · Alt+M
          integrations
        </footer>

        <HiveBottomNav onMore={() => setMoreOpen(true)} pathname={pathname} />
        <HiveMoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} pathname={pathname} />
      </div>
    </div>
  );
}
