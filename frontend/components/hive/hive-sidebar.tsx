"use client";

import Link from "next/link";
import { XIcon } from "lucide-react";

import { QueenHoneycombLogo } from "@/components/auth/queen-honeycomb-logo";
import { HIVE_NAV_PRIMARY, isNavItemActive } from "@/lib/hive-nav-primary";
import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";
import { cn } from "@/lib/utils";

export { HIVE_NAV_PRIMARY } from "@/lib/hive-nav-primary";

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

function routeActive(pathname: string, href: string): boolean {
  const item = HIVE_NAV_PRIMARY.find((row) => row.href === href);
  if (item) {
    return isNavItemActive(pathname, item);
  }
  if (href.startsWith("/#")) {
    return pathname === "/";
  }
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

interface HiveSidebarProps {
  pathname: string;
  /** Mobile / tablet (&lt; lg): slide-over drawer visibility. */
  mobileOpen: boolean;
  onMobileClose: () => void;
}

function navLinkClass(pathname: string, href: string): string {
  const active = routeActive(pathname, href);
  return cn(
    "flex items-center gap-3 rounded-xl px-3 py-2.5 transition touch-manipulation min-h-[44px]",
    active
      ? "bg-[rgb(61_53_38/0.92)] text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.35)]"
      : "border border-transparent text-zinc-400 hover:border-cyan/20 hover:bg-white/[0.03] hover:text-pollen active:bg-white/[0.06]",
  );
}

function SidebarBrand({ onMobileClose }: { onMobileClose?: () => void }) {
  return (
    <div className="mb-6 flex h-14 shrink-0 items-center gap-2 border-b border-[#1a1a3e]/90 px-4">
      <Link href="/" className="flex min-w-0 flex-1 items-center gap-2.5" prefetch onClick={() => onMobileClose?.()}>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center overflow-visible">
          <QueenHoneycombLogo size={36} aria-hidden />
        </div>
        <span className="truncate font-[family-name:var(--font-poppins)] text-[15px] font-bold tracking-tight text-[#FFB800]">
          Queenswarm
        </span>
      </Link>
      {onMobileClose ? (
        <button
          type="button"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan/20 text-zinc-400 hover:border-pollen/35 hover:text-pollen lg:hidden"
          aria-label="Close navigation"
          onClick={onMobileClose}
        >
          <XIcon className="h-5 w-5" aria-hidden />
        </button>
      ) : null}
    </div>
  );
}

function SidebarNav({
  pathname,
  linkClassFn,
  onNavigate,
}: {
  pathname: string;
  linkClassFn: (href: string) => string;
  onNavigate?: () => void;
}) {
  return (
    <nav aria-label="Hive navigation" className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 hive-scrollbar">
      {HIVE_NAV_PRIMARY.map((item) => {
        const { href, label, Icon } = item;
        const active = isNavItemActive(pathname, item);
        return (
          <Link key={href} href={href} prefetch className={linkClassFn(href)} onClick={() => onNavigate?.()}>
            <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-pollen" : "text-zinc-500")} aria-hidden />
            <span className="whitespace-nowrap font-[family-name:var(--font-poppins)] text-[13px] font-medium">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** Desktop: persistent 220px rail. Mobile: off-canvas drawer with same links + safe-area padding. */
export function HiveSidebar({ pathname, mobileOpen, onMobileClose }: HiveSidebarProps) {
  function linkClass(href: string): string {
    return navLinkClass(pathname, href);
  }

  async function handleLogout(): Promise<void> {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch {
      /* still clear mirrored client stores */
    }
    clearClientSessionArtifacts();
    window.location.assign("/login");
  }

  return (
    <>
      {/* Mobile drawer */}
      <div
        className={cn(
          "fixed inset-0 z-[70] bg-black/72 backdrop-blur-sm transition-opacity duration-200 lg:hidden",
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        aria-hidden={!mobileOpen}
        onClick={onMobileClose}
      />
      <aside
        className={cn(
          "fixed left-0 top-0 z-[80] flex h-[100dvh] w-[min(92vw,288px)] flex-col overflow-hidden border-r border-[#1a1a3e]/90 bg-[#0d0d2b]/98 py-[max(0.5rem,env(safe-area-inset-top))] shadow-[8px_0_48px_rgb(0_0_0/0.55)] transition-transform duration-200 ease-out lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full pointer-events-none",
        )}
        aria-hidden={!mobileOpen}
      >
        <SidebarBrand onMobileClose={onMobileClose} />
        <SidebarNav pathname={pathname} linkClassFn={linkClass} onNavigate={onMobileClose} />
        <div className="mt-auto shrink-0 border-t border-[#1e1e35] px-2 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3">
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="group flex min-h-[44px] w-full items-center gap-2.5 rounded-lg border border-transparent px-3 py-[9px] text-left font-[family-name:var(--font-poppins)] text-[13px] text-[#5a5a7a] transition-all duration-150 hover:border-[rgba(255,51,102,0.2)] hover:bg-[rgba(255,51,102,0.08)] hover:text-[#FF3366]"
          >
            Log out
          </button>
        </div>
      </aside>

      {/* Desktop rail */}
      <aside className="sticky top-0 z-30 hidden h-screen w-[220px] min-w-[220px] shrink-0 flex-col overflow-y-auto border-r border-[#1a1a3e]/90 bg-[#0d0d2b]/95 py-6 hive-scrollbar lg:flex">
        <SidebarBrand />
        <SidebarNav pathname={pathname} linkClassFn={linkClass} />
        <div className="mt-auto shrink-0 border-t border-[#1e1e35] px-2 pb-6 pt-3">
          <p className="mb-2 px-3 font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-600">
            Shortcuts · desktop
          </p>
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="group flex w-full items-center gap-2.5 rounded-lg border border-transparent px-3 py-[9px] text-left font-[family-name:var(--font-poppins)] text-[13px] text-[#5a5a7a] transition-all duration-150 hover:border-[rgba(255,51,102,0.2)] hover:bg-[rgba(255,51,102,0.08)] hover:text-[#FF3366]"
          >
            Log out
          </button>
        </div>
      </aside>
    </>
  );
}
