"use client";

import Link from "next/link";
import {
  ClipboardList,
  GitBranch,
  Hexagon,
  LayoutDashboardIcon,
  MicIcon,
  Settings,
  Share2,
  type LucideIcon,
} from "lucide-react";

import { QueenHoneycombLogo } from "@/components/auth/queen-honeycomb-logo";
import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  Icon: LucideIcon;
}

/** Primary cockpit routes + in-page anchors (mockup-style IA). */
export const HIVE_NAV_PRIMARY: NavItem[] = [
  { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon },
  { href: "/tasks/new", label: "Nový task", Icon: ClipboardList },
  { href: "/#hive-live-swarm", label: "Živá sieť", Icon: Hexagon },
  { href: "/swarms", label: "Swarmy", Icon: Share2 },
  { href: "/hierarchy", label: "Hierarchia", Icon: GitBranch },
  { href: "/ballroom", label: "Ballroom", Icon: MicIcon },
  { href: "/settings/security", label: "Nastavenia", Icon: Settings },
];

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
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

interface HiveSidebarProps {
  pathname: string;
}

/** Fixed-width 220px left rail. */
export function HiveSidebar({ pathname }: HiveSidebarProps) {
  function linkClass(href: string): string {
    const active = routeActive(pathname, href);
    return cn(
      "flex items-center gap-3 rounded-xl px-3 py-2.5 transition",
      active
        ? "bg-[rgb(61_53_38/0.92)] text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.35)]"
        : "border border-transparent text-zinc-400 hover:border-cyan/20 hover:bg-white/[0.03] hover:text-pollen",
    );
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
    <aside className="sticky top-0 z-30 hidden h-screen w-[220px] min-w-[220px] shrink-0 flex-col overflow-y-auto border-r border-[#1a1a3e]/90 bg-[#0d0d2b]/95 py-6 hive-scrollbar lg:flex">
      <div className="mb-6 flex h-14 shrink-0 items-center gap-3 border-b border-[#1a1a3e]/90 px-4">
        <Link href="/" className="flex min-w-0 flex-1 items-center gap-2.5" prefetch>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center overflow-visible">
            <QueenHoneycombLogo size={36} aria-hidden />
          </div>
          <span className="truncate font-[family-name:var(--font-poppins)] text-[15px] font-bold tracking-tight text-[#FFB800]">
            Queenswarm
          </span>
        </Link>
      </div>

      <nav aria-label="Hive navigation" className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2">
        {HIVE_NAV_PRIMARY.map(({ href, label, Icon }) => {
          const active = routeActive(pathname, href);
          return (
            <Link key={href} href={href} prefetch className={linkClass(href)}>
              <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-pollen" : "text-zinc-500")} aria-hidden />
              <span className="whitespace-nowrap font-[family-name:var(--font-poppins)] text-[13px] font-medium">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto shrink-0 border-t border-[#1e1e35] px-2 pb-6 pt-3">
        <button
          type="button"
          onClick={() => void handleLogout()}
          className="group flex w-full items-center gap-2.5 rounded-lg border border-transparent px-3 py-[9px] text-left font-[family-name:var(--font-poppins)] text-[13px] text-[#5a5a7a] transition-all duration-150 hover:border-[rgba(255,51,102,0.2)] hover:bg-[rgba(255,51,102,0.08)] hover:text-[#FF3366]"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="shrink-0"
            aria-hidden
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          <span>Odhlásiť sa</span>
        </button>
      </div>
    </aside>
  );
}
