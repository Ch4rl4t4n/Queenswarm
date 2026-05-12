"use client";

import Link from "next/link";
import {
  BookOpenIcon,
  BotIcon,
  FlaskConicalIcon,
  GitBranchIcon,
  HexagonIcon,
  LayoutDashboardIcon,
  LineChartIcon,
  ListTodoIcon,
  MicIcon,
  PaletteIcon,
  PuzzleIcon,
  SettingsIcon,
  TrophyIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { StatusIndicator } from "@/components/ui/status-indicator";
import type { DashboardSummary } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  Icon: typeof LayoutDashboardIcon;
}

/** QueenSwarm nav — aligns with cockpit mock IA. */
export const HIVE_NAV_PRIMARY: NavItem[] = [
  { href: "/", label: "Dashboard", Icon: LayoutDashboardIcon },
  { href: "/agents", label: "Agents", Icon: BotIcon },
  { href: "/swarms", label: "Swarms", Icon: HexagonIcon },
  { href: "/tasks", label: "Tasks", Icon: ListTodoIcon },
  { href: "/workflows", label: "Workflows", Icon: GitBranchIcon },
  { href: "/recipes", label: "Recipes", Icon: BookOpenIcon },
  { href: "/leaderboard", label: "Leaderboard", Icon: TrophyIcon },
  { href: "/ballroom", label: "Ballroom", Icon: MicIcon },
  { href: "/costs", label: "Costs", Icon: LineChartIcon },
  { href: "/settings", label: "Settings", Icon: SettingsIcon },
];

export const HIVE_NAV_LABS: NavItem[] = [
  { href: "/simulations", label: "Simulations", Icon: FlaskConicalIcon },
  { href: "/plugins", label: "Plugins", Icon: PuzzleIcon },
  { href: "/design-system", label: "Design system", Icon: PaletteIcon },
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
  return href === "/settings"
    ? pathname.startsWith("/settings")
    : pathname === href || (href !== "/" && pathname.startsWith(href));
}

interface HiveSidebarProps {
  pathname: string;
}

/** Left rail · honey active chip · cyan hive vitality bar — Figma-aligned. */
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
      "flex items-center justify-center gap-0 rounded-xl py-2.5 transition group-hover:justify-start group-hover:gap-3 group-hover:px-3",
      active
        ? "bg-[rgb(61_53_38/0.92)] text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.35)]"
        : "border border-transparent px-2 text-zinc-400 hover:border-cyan/20 hover:bg-white/[0.03] hover:text-pollen",
    );
  }

  return (
    <aside className="group sticky top-0 z-30 hidden h-screen w-16 shrink-0 flex-col overflow-hidden border-r border-[#1a1a3e]/90 bg-[#0d0d2b]/95 py-6 transition-[width] duration-300 ease-in-out hover:w-56 lg:flex">
      <div className="mb-6 flex h-14 shrink-0 items-center overflow-hidden border-b border-[#1a1a3e] px-3">
        <Link href="/" className="flex min-w-0 items-center" prefetch>
        <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0" aria-hidden="true">
          <polygon points="16,1 30,9 30,23 16,31 2,23 2,9" fill="#0d0d2b" stroke="#FFB800" strokeWidth="1.5" />
          <text x="16" y="21" textAnchor="middle" fontSize="11">
            🐝
          </text>
        </svg>
        <span
          className="ml-2 whitespace-nowrap font-[family-name:var(--font-space-grotesk)] text-sm font-bold text-[#FFB800] opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        >
          Queenswarm
        </span>
        </Link>
      </div>

      <nav aria-label="Hive navigation" className="flex flex-1 flex-col gap-0.5 overflow-y-auto hive-scrollbar px-1">
        {HIVE_NAV_PRIMARY.map(({ href, label, Icon }) => {
          const active = routeActive(pathname, href);
          return (
            <Link key={href} href={href} prefetch className={linkClass(href)}>
              <Icon className={cn("h-4 w-4 shrink-0", active ? "text-pollen" : "text-zinc-500")} aria-hidden />
              <span className="opacity-0 transition-opacity duration-200 group-hover:opacity-100 whitespace-nowrap font-[family-name:var(--font-inter)] text-sm font-medium">
                {label}
              </span>
            </Link>
          );
        })}
        <p className="mt-5 truncate px-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.22em] text-cyan/40 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-hover:px-3">
          Labs
        </p>
        {HIVE_NAV_LABS.map(({ href, label, Icon }) => (
          <Link key={href} href={href} prefetch className={linkClass(href)}>
            <Icon className="h-4 w-4 shrink-0 text-cyan/45" aria-hidden />
            <span className="opacity-0 transition-opacity duration-200 group-hover:opacity-100 whitespace-nowrap font-[family-name:var(--font-inter)] text-sm font-medium">
              <span className={routeActive(pathname, href) ? "" : "text-zinc-500"}>{label}</span>
            </span>
          </Link>
        ))}
      </nav>

      <div className="mt-auto rounded-xl border border-cyan/15 bg-black/35 px-3 py-3">
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
