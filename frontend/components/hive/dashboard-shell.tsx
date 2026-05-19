"use client";

import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DashboardLayoutProvider } from "@/components/hive/dashboard-layout-provider";
import { DashboardSettingsPanel } from "@/components/hive/dashboard-settings-panel";
import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { BallroomFab } from "@/components/hive/ballroom-fab";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import { hiveShortcutHrefForKey } from "@/lib/hive-sidebar-shortcuts";
import { MEDIA_QUERIES } from "@/lib/breakpoints";
import { cn } from "@/lib/utils";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import type { DashboardSummary, TenantListPayload } from "@/lib/hive-types";

interface DashboardShellProps {
  children: ReactNode;
}

const SIDEBAR_W = "lg:left-[272px]";

/** Desktop Ctrl+letter shortcuts (ignored when typing in inputs). */
function useDesktopHiveShortcuts(router: ReturnType<typeof useRouter>): void {
  useEffect(() => {
    const mq = window.matchMedia(MEDIA_QUERIES.desktop);
    if (!mq.matches) {
      return undefined;
    }

    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable || t.tagName === "SELECT")) {
        return;
      }
      if (!e.ctrlKey || e.altKey || e.metaKey) {
        return;
      }
      const href = hiveShortcutHrefForKey(e.key, PHASE70_CONSOLIDATED_NAV_ENABLED);
      if (!href) {
        return;
      }
      e.preventDefault();
      router.push(href);
      router.refresh();
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);
}

/**
 * Shell layout:
 * - Desktop (≥1024): sidebar only — no duplicated top bar (per tuned cockpit IA).
 * - Mobile / tablet (&lt;1024): drawer, bottom nav, mobile header, FAB.
 */
export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [tenants, setTenants] = useState<TenantListPayload | null>(null);
  const [tenantSwitching, setTenantSwitching] = useState(false);
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
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/api/proxy/auth/tenants", { credentials: "include" });
        if (!res.ok) {
          return;
        }
        const body = (await res.json()) as TenantListPayload;
        if (alive) {
          setTenants(body);
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
    <DashboardLayoutProvider>
      <div className="relative z-[1] flex min-h-screen min-w-0 bg-transparent text-[var(--qs-text)]">
        <HiveSidebar
          pathname={pathname}
          mobileOpen={mobileDrawerOpen}
          onMobileClose={closeDrawer}
          summary={summary}
          tenants={tenants}
          tenantSwitching={tenantSwitching}
          onTenantSwitch={(tenantId) => {
            setTenantSwitching(true);
            void fetch("/api/auth/tenant-switch", {
              method: "POST",
              credentials: "include",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ tenant_id: tenantId }),
            })
              .then(() => {
                router.refresh();
              })
              .finally(() => setTenantSwitching(false));
          }}
        />
        <DashboardSettingsPanel />

        <div
          className={cn(
            "relative z-[1] flex min-h-dvh min-w-0 flex-1 flex-col",
            pathname.startsWith("/ballroom") && "h-dvh max-h-dvh overflow-hidden",
          )}
        >
          <div
            aria-hidden
            className={cn(
              "pointer-events-none fixed inset-y-0 right-0 z-[-1] hive-bg-pattern",
              SIDEBAR_W,
              "opacity-[0.72] max-lg:opacity-40",
            )}
          />
          <div
            aria-hidden
            className={cn(
              "pointer-events-none fixed inset-y-0 right-0 z-[-1] hidden bg-[radial-gradient(ellipse_at_50%_-10%,rgba(255,184,0,0.07),transparent_55%)] lg:block",
              SIDEBAR_W,
            )}
          />

          <HiveMobileHeader pathname={pathname} summary={summary} onOpenNav={() => setMobileDrawerOpen(true)} />

          <main
            data-hive-shell="canvas"
            className={cn(
              "relative mx-auto w-full min-w-0 flex-1",
              "px-4 pt-4 pb-[calc(var(--qs-shell-bottom-nav-h)+1.25rem+env(safe-area-inset-bottom))]",
              "md:px-5 md:pt-5",
              "lg:max-w-[1400px] lg:px-9 lg:pt-8 lg:pb-16",
              pathname.startsWith("/ballroom") &&
                "flex min-h-0 flex-col overflow-hidden pb-[calc(var(--qs-shell-bottom-nav-h)+0.5rem+env(safe-area-inset-bottom))] lg:pb-8",
            )}
          >
            {children}
          </main>

          <HiveBottomNav onMore={() => setMoreOpen(true)} pathname={pathname} />
          <BallroomFab />
          <HiveMoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} pathname={pathname} />
        </div>
      </div>
    </DashboardLayoutProvider>
  );
}
