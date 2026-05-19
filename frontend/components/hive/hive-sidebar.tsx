"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { Check, ChevronDown, LogOut, XIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { QueenHoneycombLogo } from "@/components/auth/queen-honeycomb-logo";
import { DashboardSettingsTrigger } from "@/components/hive/dashboard-settings-panel";
import { SidebarShortcuts } from "@/components/hive/sidebar-shortcuts";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { hiveGet } from "@/lib/api";
import {
  HIVE_NAV_PRIMARY,
  HIVE_SIDEBAR_SECONDARY,
  isNavItemActive,
  type HiveNavItem,
} from "@/lib/hive-nav-primary";
import type { DashboardSummary, SwarmBoardResponse, TenantListPayload, TenantViewRow } from "@/lib/hive-types";
import { localizeNavLabel, localizePhrase } from "@/lib/ui-copy";
import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";
import { cn } from "@/lib/utils";

export { HIVE_NAV_PRIMARY } from "@/lib/hive-nav-primary";

const SIDEBAR_WIDTH_PX = 272;

interface SidebarNavCounts {
  swarms: number | null;
  foragers: number | null;
}

function clearClientSessionArtifacts(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem("qs_token");
  localStorage.removeItem("qs_dashboard_at");
  sessionStorage.removeItem("qs_pre_auth_token");
  sessionStorage.removeItem("qs_pre_auth");
  const base = "path=/; max-age=0; SameSite=Strict";
  document.cookie = `qs_token=; ${base}`;
  document.cookie = `${QS_ACCESS}=; ${base}`;
  document.cookie = `${QS_REFRESH}=; ${base}`;
}

interface HiveSidebarProps {
  pathname: string;
  mobileOpen: boolean;
  onMobileClose: () => void;
  summary?: DashboardSummary | null;
  tenants?: TenantListPayload | null;
  onTenantSwitch?: (tenantId: string) => void;
  tenantSwitching?: boolean;
}

function navBadgeForHref(href: string, summary: DashboardSummary | null | undefined, counts: SidebarNavCounts): number | null {
  if (href === "/agents" || href.startsWith("/agents")) {
    return summary?.agents.total ?? null;
  }
  if (href === "/tasks" || href.startsWith("/tasks")) {
    return summary?.tasks.pending ?? null;
  }
  if (href === "/swarms") {
    return counts.swarms;
  }
  if (href === "/foragers") {
    return counts.foragers;
  }
  return null;
}

function tenantSubtitle(tenant: TenantViewRow, language: "en" | "sk"): string {
  const role = tenant.role.replace(/_/g, " ");
  const cap = role.charAt(0).toUpperCase() + role.slice(1);
  return localizePhrase(language, {
    en: `${cap} · workspace`,
    sk: `${cap} · workspace`,
  });
}

function SidebarBrand({ onMobileClose }: { onMobileClose?: () => void }) {
  return (
    <div className="hive-sidebar-brand">
      <Link href="/" className="flex min-w-0 flex-1 items-center gap-3" prefetch onClick={() => onMobileClose?.()}>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-visible drop-shadow-[0_0_12px_rgba(253,185,39,0.55)]">
          <QueenHoneycombLogo size={40} aria-hidden />
        </div>
        <div className="min-w-0">
          <span className="block truncate font-[family-name:var(--font-poppins)] text-[17px] font-bold tracking-tight text-[var(--qs-text)]">
            Queenswarm
          </span>
          <span className="block truncate text-[10px] font-medium uppercase tracking-[0.18em] text-[var(--qs-text-3)]">
            Hive Control · V4
          </span>
        </div>
      </Link>
      {onMobileClose ? (
        <button
          type="button"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] border border-[var(--qs-border)] text-[var(--qs-text-3)] hover:border-[var(--qs-border-2)] hover:text-pollen lg:hidden"
          aria-label="Close navigation"
          onClick={onMobileClose}
        >
          <XIcon className="h-5 w-5" aria-hidden />
        </button>
      ) : null}
    </div>
  );
}

function SidebarTenantSwitcher({
  tenants,
  onTenantSwitch,
  tenantSwitching,
  language,
}: {
  tenants?: TenantListPayload | null;
  onTenantSwitch?: (tenantId: string) => void;
  tenantSwitching?: boolean;
  language: "en" | "sk";
}) {
  const [open, setOpen] = useState(false);
  const list = tenants?.tenants ?? [];
  const current = list.find((t) => t.id === tenants?.current_tenant_id) ?? list[0];

  if (!current) {
    return (
      <div className="hive-tenant-switch hive-tenant-switch--static">
        <div className="hive-tenant-mark">Q</div>
        <div className="hive-tenant-copy">
          <span className="hive-tenant-title">Queenswarm</span>
          <span className="hive-tenant-sub">Hive Pro · workspace</span>
        </div>
      </div>
    );
  }

  const canSwitch = list.length > 1 && onTenantSwitch;

  return (
    <div className="relative px-3">
      <button
        type="button"
        className="hive-tenant-switch w-full text-left"
        aria-expanded={open}
        disabled={!canSwitch || tenantSwitching}
        onClick={() => {
          if (canSwitch) {
            setOpen((v) => !v);
          }
        }}
      >
        <div className="hive-tenant-mark">{current.name.charAt(0).toUpperCase()}</div>
        <div className="hive-tenant-copy min-w-0">
          <span className="hive-tenant-title truncate">{current.name}</span>
          <span className="hive-tenant-sub truncate">{tenantSubtitle(current, language)}</span>
        </div>
        {canSwitch ? <ChevronDown className={cn("h-4 w-4 shrink-0 text-[var(--qs-text-3)] transition", open && "rotate-180")} aria-hidden /> : null}
      </button>
      {open && canSwitch ? (
        <div className="hive-tenant-dropdown">
          {list.map((tenant) => {
            const active = tenant.id === current.id;
            return (
              <button
                key={tenant.id}
                type="button"
                className="hive-tenant-option"
                onClick={() => {
                  setOpen(false);
                  if (!active) {
                    onTenantSwitch?.(tenant.id);
                  }
                }}
              >
                <div className="hive-tenant-mark">{tenant.name.charAt(0).toUpperCase()}</div>
                <div className="hive-tenant-copy min-w-0 text-left">
                  <span className="hive-tenant-title truncate">{tenant.name}</span>
                  <span className="hive-tenant-sub truncate">{tenantSubtitle(tenant, language)}</span>
                </div>
                {active ? <Check className="h-3.5 w-3.5 shrink-0 text-pollen" aria-hidden /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function NavCountBadge({ count, active }: { count: number; active: boolean }) {
  return (
    <span className={cn("hive-nav-count", active && "hive-nav-count--active")}>{count}</span>
  );
}

function SidebarNavLink({
  item,
  pathname,
  language,
  summary,
  counts,
  onNavigate,
  trailing,
}: {
  item: HiveNavItem;
  pathname: string;
  language: "en" | "sk";
  summary?: DashboardSummary | null;
  counts: SidebarNavCounts;
  onNavigate?: () => void;
  trailing?: ReactNode;
}) {
  const { href, label, Icon } = item;
  const active = isNavItemActive(pathname, item);
  const badge = navBadgeForHref(href, summary, counts);

  return (
    <div className={cn("hive-nav-row", active && "hive-nav-row--active")}>
      <Link href={href} prefetch className="hive-nav-item" onClick={() => onNavigate?.()}>
        <span className="hive-nav-icon">
          <Icon className="h-[18px] w-[18px]" aria-hidden />
        </span>
        <span className="hive-nav-label">{localizeNavLabel(label, language)}</span>
        {badge != null ? <NavCountBadge count={badge} active={active} /> : null}
      </Link>
      {trailing}
    </div>
  );
}

function SidebarNav({
  pathname,
  language,
  summary,
  counts,
  onNavigate,
}: {
  pathname: string;
  language: "en" | "sk";
  summary?: DashboardSummary | null;
  counts: SidebarNavCounts;
  onNavigate?: () => void;
}) {
  return (
    <nav aria-label="Hive navigation" className="hive-sidebar-nav hive-scrollbar">
      {HIVE_NAV_PRIMARY.map((item) => {
        const isDashboard = item.href === "/";
        return (
          <SidebarNavLink
            key={item.href}
            item={item}
            pathname={pathname}
            language={language}
            summary={summary}
            counts={counts}
            onNavigate={onNavigate}
            trailing={
              isDashboard ? (
                <span data-dash-settings-trigger className="mr-1.5">
                  <DashboardSettingsTrigger />
                </span>
              ) : undefined
            }
          />
        );
      })}

      <div className="hive-nav-divider" aria-hidden />

      {HIVE_SIDEBAR_SECONDARY.map((item) => (
        <SidebarNavLink
          key={item.href}
          item={item}
          pathname={pathname}
          language={language}
          summary={summary}
          counts={counts}
          onNavigate={onNavigate}
        />
      ))}
    </nav>
  );
}

function SidebarFooter({
  language,
  swarmCount,
  onLogout,
  onNavigate,
}: {
  language: "en" | "sk";
  swarmCount: number | null;
  onLogout: () => void;
  onNavigate?: () => void;
}) {
  const statusSub = swarmCount != null
    ? localizePhrase(language, {
        en: `${swarmCount} swarms · global mind`,
        sk: `${swarmCount} swarmov · globálna myseľ`,
      })
    : localizePhrase(language, { en: "Global mind · 5 min sync", sk: "Globálna myseľ · sync 5 min" });

  return (
    <div className="hive-sidebar-footer">
      <div className="hive-sidebar-status">
        <span className="hive-pulse-dot shrink-0" aria-hidden />
        <div className="min-w-0 leading-tight">
          <span className="block text-xs font-semibold text-[var(--qs-green)]">
            {localizePhrase(language, { en: "Hive synced", sk: "Hive sync" })}
          </span>
          <span className="mt-0.5 block text-[10px] text-[var(--qs-text-3)]">{statusSub}</span>
        </div>
      </div>

      <SidebarShortcuts onNavigate={onNavigate} />

      <button type="button" onClick={onLogout} className="hive-logout-btn">
        <LogOut className="h-4 w-4 shrink-0" aria-hidden />
        {localizePhrase(language, { en: "Log out", sk: "Odhlásiť" })}
      </button>
    </div>
  );
}

const sidebarShellClass = "hive-sidebar-rail h-[100dvh]";

/** Desktop: persistent rail. Mobile: off-canvas drawer. */
export function HiveSidebar({
  pathname,
  mobileOpen,
  onMobileClose,
  summary,
  tenants,
  onTenantSwitch,
  tenantSwitching,
}: HiveSidebarProps) {
  const { language } = useUiLanguage();
  const [counts, setCounts] = useState<SidebarNavCounts>({ swarms: null, foragers: null });

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const [board, foragers] = await Promise.all([
          hiveGet<SwarmBoardResponse>("dashboard/swarm-board").catch(() => null),
          hiveGet<unknown[]>("foragers").catch(() => null),
        ]);
        if (!alive) {
          return;
        }
        setCounts({
          swarms: board?.sub_swarms?.length ?? null,
          foragers: Array.isArray(foragers) ? foragers.length : null,
        });
      } catch {
        /* keep nulls */
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function handleLogout(): Promise<void> {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch {
      /* still clear mirrored client stores */
    }
    clearClientSessionArtifacts();
    window.location.assign("/login");
  }

  const shellStyle = { width: SIDEBAR_WIDTH_PX, minWidth: SIDEBAR_WIDTH_PX } as const;
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mobileOpen) {
      document.documentElement.classList.remove("hive-nav-drawer-open");
      return undefined;
    }
    document.documentElement.classList.add("hive-nav-drawer-open");
    return () => document.documentElement.classList.remove("hive-nav-drawer-open");
  }, [mobileOpen]);

  const mobileDrawer = (
    <>
      <div
        className={cn(
          "hive-sidebar-backdrop lg:hidden",
          mobileOpen ? "hive-sidebar-backdrop--open" : "hive-sidebar-backdrop--closed",
        )}
        aria-hidden={!mobileOpen}
        onClick={onMobileClose}
      />
      <aside
        className={cn(
          "hive-sidebar-rail hive-sidebar-rail--mobile lg:hidden",
          sidebarShellClass,
          "py-[max(0.75rem,env(safe-area-inset-top))]",
          mobileOpen ? "hive-sidebar-rail--mobile-open" : "hive-sidebar-rail--mobile-closed",
        )}
        aria-hidden={!mobileOpen}
      >
        <SidebarBrand onMobileClose={onMobileClose} />
        <SidebarTenantSwitcher tenants={tenants} onTenantSwitch={onTenantSwitch} tenantSwitching={tenantSwitching} language={language} />
        <SidebarNav pathname={pathname} language={language} summary={summary} counts={counts} onNavigate={onMobileClose} />
        <SidebarFooter language={language} swarmCount={counts.swarms} onLogout={() => void handleLogout()} onNavigate={onMobileClose} />
      </aside>
    </>
  );

  return (
    <>
      {mounted ? createPortal(mobileDrawer, document.body) : null}

      <aside
        style={shellStyle}
        className={cn("hive-sidebar-rail hive-sidebar-rail--desktop", sidebarShellClass, "py-6")}
      >
        <SidebarBrand />
        <SidebarTenantSwitcher tenants={tenants} onTenantSwitch={onTenantSwitch} tenantSwitching={tenantSwitching} language={language} />
        <SidebarNav pathname={pathname} language={language} summary={summary} counts={counts} />
        <SidebarFooter language={language} swarmCount={counts.swarms} onLogout={() => void handleLogout()} />
      </aside>
    </>
  );
}

export const HIVE_SIDEBAR_WIDTH_PX = SIDEBAR_WIDTH_PX;
