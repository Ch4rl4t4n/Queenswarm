"use client";

import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DashboardLayoutProvider } from "@/components/hive/dashboard-layout-provider";
import { DashboardSettingsPanel } from "@/components/hive/dashboard-settings-panel";
import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { OperatorShellFab } from "@/components/hive/operator-shell-fab";
import { HiveCommandPaletteHost } from "@/components/hive/hive-command-palette-host";
import { OperatorMissionFeedProvider } from "@/components/hive/operator-mission-feed-provider";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { SkipToMainLink } from "@/components/hive/skip-to-main-link";
import { HiveMobileHeaderActionsProvider } from "@/components/hive/hive-mobile-header-actions";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { HotRouteChunkWarmer } from "@/components/hive/hot-route-chunk-warmer";
import { IdleRoutePrefetcher } from "@/components/hive/idle-route-prefetcher";
import { OPERATOR_CONTROL_PLANE_ENABLED, SINGLE_ADMIN_MODE } from "@/lib/feature-flags";
import { resyncExecutionStudioPushIfEnabled } from "@/lib/execution-studio-push-session-sync";
import { HIVE_MAIN_CONTENT_ID } from "@/lib/hive-a11y";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import { PlatformProvider } from "@/components/hive/platform-context";
import { PlatformRouteGuard } from "@/components/hive/platform-route-guard";
import { useDashboardSessionRefresh } from "@/lib/hooks/use-dashboard-session-refresh";
import { hiveGet } from "@/lib/api";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { cn } from "@/lib/utils";
import type { DashboardSummary, TenantListPayload } from "@/lib/hive-types";

interface DashboardShellProps {
  children: ReactNode;
}

const SIDEBAR_W = "lg:left-[272px]";

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

  useDashboardSessionRefresh();

  const closeDrawer = useCallback(() => setMobileDrawerOpen(false), []);

  useEffect(() => {
    if (SINGLE_ADMIN_MODE) {
      setTenants(null);
      return;
    }
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

  useEffect(() => {
    void resyncExecutionStudioPushIfEnabled();
  }, []);

  return (
    <PlatformProvider>
      <OperatorMissionFeedProvider>
      <IdleRoutePrefetcher />
      <HotRouteChunkWarmer />
      <DashboardLayoutProvider>
        <HiveMobileHeaderActionsProvider>
        <div className="relative z-[1] flex min-h-screen min-w-0 bg-transparent text-(--qs-text)">
          <HiveSidebar
            pathname={pathname}
            mobileOpen={mobileDrawerOpen}
            onMobileClose={closeDrawer}
            summary={summary}
            tenants={SINGLE_ADMIN_MODE ? null : tenants}
            tenantSwitching={SINGLE_ADMIN_MODE ? false : tenantSwitching}
            onTenantSwitch={(tenantId) => {
              if (SINGLE_ADMIN_MODE) {
                return;
              }
              setTenantSwitching(true);
              void fetch("/api/auth/tenant-switch", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tenant_id: tenantId }),
              })
                .then(async () => {
                  await resyncExecutionStudioPushIfEnabled();
                  router.refresh();
                  window.location.reload();
                })
                .finally(() => setTenantSwitching(false));
            }}
          />
          {!OPERATOR_CONTROL_PLANE_ENABLED ? <DashboardSettingsPanel /> : null}

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

            <SkipToMainLink />
            <HiveMobileHeader
              pathname={pathname}
              summary={summary}
              onOpenNav={() => setMobileDrawerOpen(true)}
            />

            <main
              id={HIVE_MAIN_CONTENT_ID}
              data-hive-shell="canvas"
              tabIndex={-1}
              className={cn(
                "relative mx-auto w-full min-w-0 flex-1",
                "px-4 pt-4 pb-[var(--qs-shell-mobile-scroll-pad)]",
                "md:px-5 md:pt-5",
                "lg:max-w-[1400px] lg:px-9 lg:pt-8 lg:pb-16",
                pathname.startsWith("/ballroom") &&
                  "flex min-h-0 flex-col overflow-hidden pb-[calc(var(--qs-shell-bottom-nav-h)+0.5rem+env(safe-area-inset-bottom))] lg:pb-8",
              )}
            >
              <PlatformRouteGuard>{children}</PlatformRouteGuard>
            </main>

            <HiveBottomNav
              onMore={() => setMoreOpen(true)}
              pathname={pathname}
              moreOpen={moreOpen}
            />
            <OperatorShellFab hidden={mobileDrawerOpen || moreOpen} />
            <HiveMoreSheet
              open={moreOpen}
              onClose={() => setMoreOpen(false)}
              pathname={pathname}
              tenants={SINGLE_ADMIN_MODE ? null : tenants}
            />
            <HiveCommandPaletteHost />
          </div>
        </div>
        </HiveMobileHeaderActionsProvider>
      </DashboardLayoutProvider>
      </OperatorMissionFeedProvider>
    </PlatformProvider>
  );
}
