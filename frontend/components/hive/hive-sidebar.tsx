"use client";

import Link from "next/link";
import {
  ClipboardList,
  GitBranch,
  Hexagon,
  LayoutDashboardIcon,
  MicIcon,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { AuthHexLogo } from "@/components/auth/auth-hex-logo";
import { StatusIndicator } from "@/components/ui/status-indicator";
import type { DashboardSummary } from "@/lib/hive-types";
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
  { href: "/#hive-hierarchy", label: "Hierarchia", Icon: GitBranch },
  { href: "/ballroom", label: "Ballroom", Icon: MicIcon },
  { href: "/settings/security", label: "Nastavenia", Icon: Settings },
];

function hiveOnlineTotals(byStatus: Record<string, number> | undefined): { online: number; total: number } {
  if (!byStatus) {
    return { online: 0, total: 0 };
  }
  const total = Object.values(byStatus).reduce((a, b) => a + b, 0);
  let offlineOrError = 0;
  for (const [k, v] of Object.entries(byStatus)) {
    const key = k.toUpperCase();
    if (key === "OFFLINE" || key === "ERROR") {
      offlineOrError += v;
    }
  }
  return { online: Math.max(0, total - offlineOrError), total };
}

function routeActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

interface HiveSidebarProps {
  pathname: string;
}

/** Fixed-width 220px left rail. */
export function HiveSidebar({ pathname }: HiveSidebarProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

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

  const { online, total } = hiveOnlineTotals(summary?.agents.by_status);
  const vitality = total > 0 ? Math.min(100, Math.round((online / total) * 100)) : 0;

  function linkClass(href: string): string {
    const active = routeActive(pathname, href);
    return cn(
      "flex items-center gap-3 rounded-xl px-3 py-2.5 transition",
      active
        ? "bg-[rgb(61_53_38/0.92)] text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.35)]"
        : "border border-transparent text-zinc-400 hover:border-cyan/20 hover:bg-white/[0.03] hover:text-pollen",
    );
  }

  return (
    <aside className="sticky top-0 z-30 hidden h-screen w-[220px] min-w-[220px] shrink-0 flex-col overflow-y-auto border-r border-[#1a1a3e]/90 bg-[#0d0d2b]/95 py-6 hive-scrollbar lg:flex">
      <div className="mb-6 flex h-14 shrink-0 items-center gap-3 border-b border-[#1a1a3e]/90 px-4">
        <Link href="/" className="flex min-w-0 flex-1 items-center gap-2.5" prefetch>
          <div className="h-9 w-9 shrink-0">
            <AuthHexLogo className="h-9 w-9" aria-hidden />
          </div>
          <span className="truncate font-[family-name:var(--font-space-grotesk)] text-[15px] font-bold tracking-tight text-[#FFB800]">
            Queenswarm
          </span>
        </Link>
      </div>

      <nav aria-label="Hive navigation" className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2">
        {HIVE_NAV_PRIMARY.map(({ href, label, Icon }) => {
          const active = routeActive(pathname, href);
          return (
            <Link key={href} href={href} prefetch className={linkClass(href)}>
              <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-pollen" : "text-zinc-500")} aria-hidden />
              <span className="whitespace-nowrap font-[family-name:var(--font-inter)] text-[13px] font-medium">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-xl border border-cyan/15 bg-black/35 px-4 py-3">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
          Hive status
        </p>
        <div className="mt-3 flex items-center justify-between gap-2">
          <span className="font-[family-name:var(--font-space-grotesk)] text-sm font-semibold text-[#fafafa]">
            {total > 0 ? `${online}/${total}` : "—"}
          </span>
          <StatusIndicator
            tone={total > 0 && online === total ? "online" : online > 0 ? "idle" : "offline"}
            label="Online"
            pulse={online > 0 && online === total}
          />
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-black/60">
          <div
            className="h-full rounded-full bg-data shadow-[0_0_12px_rgb(0_255_255/0.45)] transition-[width]"
            style={{ width: `${vitality}%` }}
          />
        </div>
      </div>
    </aside>
  );
}
