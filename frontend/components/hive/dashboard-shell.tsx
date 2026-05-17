"use client";

import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HiveBottomNav } from "@/components/hive/hive-bottom-nav";
import { BallroomFab } from "@/components/hive/ballroom-fab";
import { HiveMobileHeader } from "@/components/hive/hive-mobile-header";
import { HiveMoreSheet } from "@/components/hive/hive-more-sheet";
import { HiveSidebar } from "@/components/hive/hive-sidebar";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { keyboardLegendText, shortcutTargets } from "@/lib/hive-navigation-mode";
import type { DashboardSummary, TenantListPayload } from "@/lib/hive-types";

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
    const targets = shortcutTargets(PHASE70_CONSOLIDATED_NAV_ENABLED);

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
          go(targets.home);
          break;
        case "t":
          e.preventDefault();
          go(targets.tasks);
          break;
        case "b":
          e.preventDefault();
          go("/ballroom");
          break;
        case "o":
          e.preventDefault();
          go(targets.knowledge);
          break;
        case "m":
          e.preventDefault();
          go(targets.integrations);
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
    <div className="relative flex min-h-screen bg-hive-bg text-[#fafafa]">
      <HiveSidebar pathname={pathname} mobileOpen={mobileDrawerOpen} onMobileClose={closeDrawer} />

      <div className="relative flex min-h-dvh flex-1 flex-col">
        <div
          aria-hidden
          className={`pointer-events-none fixed inset-y-0 right-0 z-[-1] hive-bg-pattern opacity-[0.72] ${SIDEBAR_W}`}
        />
        <div
          aria-hidden
          className={`pointer-events-none fixed inset-y-0 right-0 z-[-1] bg-[radial-gradient(ellipse_at_50%_-10%,rgba(255,184,0,0.07),transparent_55%)] ${SIDEBAR_W}`}
        />

        <HiveMobileHeader pathname={pathname} summary={summary} onOpenNav={() => setMobileDrawerOpen(true)} />

        {tenants && tenants.tenants.length > 1 ? (
          <div className="sticky top-0 z-42 border-b border-cyan/[0.12] bg-hive-void/90 px-4 py-2.5 backdrop-blur-md">
            <div className="mx-auto flex w-full max-w-[1400px] items-center justify-end gap-2 text-[11px] text-zinc-300 lg:px-5">
              <span className="uppercase tracking-[0.14em] text-zinc-500">Tenant</span>
              <select
                className="min-h-[36px] rounded-md border border-cyan/25 bg-black/45 px-2 py-1 text-xs text-pollen disabled:opacity-60"
                value={tenants.current_tenant_id ?? ""}
                disabled={tenantSwitching}
                onChange={(e) => {
                  const tenantId = e.target.value;
                  if (!tenantId) {
                    return;
                  }
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
              >
                {tenants.tenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
              <a href="/manual" className="qs-btn qs-btn--ghost qs-btn--sm whitespace-nowrap">
                Open manual
              </a>
            </div>
          </div>
        ) : null}

        <main data-hive-shell="canvas" className="relative mx-auto w-full max-w-[1400px] flex-1 px-4 pb-[calc(7rem+env(safe-area-inset-bottom))] pt-8 md:pb-20 lg:px-9 lg:pb-16">
          {children}
        </main>

        <footer className="hidden border-t border-cyan/10 py-6 text-center font-(family-name:--font-poppins) text-[10px] text-cyan/45 lg:block">
          {keyboardLegendText(PHASE70_CONSOLIDATED_NAV_ENABLED)}
        </footer>

        <HiveBottomNav onMore={() => setMoreOpen(true)} pathname={pathname} />
        <BallroomFab />
        <HiveMoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} pathname={pathname} />
      </div>
    </div>
  );
}
