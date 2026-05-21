"use client";

import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DashboardLayoutProvider } from "@/components/hive/dashboard-layout-provider";
import { DashboardSettingsPanel } from "@/components/hive/dashboard-settings-panel";
import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { BallroomFab } from "@/components/hive/ballroom-fab";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { HiveMobileHeaderActionsProvider } from "@/components/hive/hive-mobile-header-actions";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { IdleRoutePrefetcher } from "@/components/hive/idle-route-prefetcher";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import { PlatformProvider } from "@/components/hive/platform-context";
import { PlatformRouteGuard } from "@/components/hive/platform-route-guard";
import { useDashboardSessionRefresh } from "@/lib/hooks/use-dashboard-session-refresh";
import { hiveGet } from "@/lib/api";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
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
  useDashboardSessionRefresh();

  const closeDrawer = useCallback(() => setMobileDrawerOpen(false), []);

  useEffect(() => {
    let alive = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const body = await hiveGet<DashboardSummary>("dashboard/summary");
          if (alive) {
            setSummary(body);
          }
        } catch {
          /* offline */
        }
      })();
    }, DASHBOARD_BOOT_STAGGER_MS.shellSummary);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const body = await hiveGet<TenantListPayload>("auth/tenants");
          if (alive) {
            setTenants(body);
          }
        } catch {
          /* offline */
        }
      })();
    }, DASHBOARD_BOOT_STAGGER_MS.shellTenants);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    closeDrawer();
  }, [pathname, closeDrawer]);

  return (
    <PlatformProvider>
      <IdleRoutePrefetcher />
      <DashboardLayoutProvider>
        <HiveMobileHeaderActionsProvider>
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
                  window.location.reload();
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

            <HiveMobileHeader summary={summary} onOpenNav={() => setMobileDrawerOpen(true)} />

            <main
              data-hive-shell="canvas"
              className={cn(
                "relative mx-auto w-full min-w-0 flex-1",
                "px-4 pt-4 pb-[calc(var(--qs-shell-bottom-nav-h)+4.25rem+env(safe-area-inset-bottom))]",
                "md:px-5 md:pt-5",
                "lg:max-w-[1400px] lg:px-9 lg:pt-8 lg:pb-16",
                pathname.startsWith("/ballroom") &&
                  "flex min-h-0 flex-col overflow-hidden pb-[calc(var(--qs-shell-bottom-nav-h)+0.5rem+env(safe-area-inset-bottom))] lg:pb-8",
              )}
            >
              <PlatformRouteGuard>{children}</PlatformRouteGuard>
            </main>

            <HiveBottomNav onMore={() => setMoreOpen(true)} pathname={pathname} />
            <BallroomFab hidden={mobileDrawerOpen || moreOpen} />
            <HiveMoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} pathname={pathname} tenants={tenants} />
          </div>
        </div>
        </HiveMobileHeaderActionsProvider>
      </DashboardLayoutProvider>
    </PlatformProvider>
  );
}
