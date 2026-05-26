"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Hexagon, LayoutDashboard, ListTodo, Mic, Plug, Users } from "lucide-react";
import type { JSX } from "react";

import { hubEcosystemLanes, type HubEcosystemPreset } from "@/lib/hub-ecosystem-lanes";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { useCenterActiveInScrollRow } from "@/lib/hooks/use-center-active-in-scroll-row";
import { cn } from "@/lib/utils";

const PRESET_KICKER: Record<
  HubEcosystemPreset,
  { icon: typeof Mic; label: string; href: string }
> = {
  ballroom: { icon: Mic, label: "Ecosystem", href: "/ballroom" },
  agents: { icon: Users, label: "Ecosystem", href: "/agents" },
  tasks: { icon: ListTodo, label: "Ecosystem", href: "/tasks" },
  knowledge: { icon: Hexagon, label: "Ecosystem", href: "/knowledge" },
  dashboard: { icon: LayoutDashboard, label: "Ecosystem", href: hiveOverviewHref() },
  integrations: { icon: Plug, label: "Ecosystem", href: "/integrations" },
};

interface HubEcosystemStripProps {
  preset: HubEcosystemPreset;
  /** Optional DOM id for hash deep-links and E2E. */
  id?: string;
}

function laneIsActive(pathname: string, href: string): boolean {
  const base = href.split("#")[0] ?? href;
  if (base === "/" || base === "/cockpit" || base === "/dashboard") {
    return pathname === base;
  }
  return pathname === base || pathname.startsWith(`${base}/`);
}

/** Compact cross-linked ecosystem shortcuts on consolidated hub pages. */
export function HubEcosystemStrip({ preset, id }: HubEcosystemStripProps): JSX.Element {
  const pathname = usePathname();
  const lanes = hubEcosystemLanes(preset);
  const kicker = PRESET_KICKER[preset];
  const KickerIcon = kicker.icon;
  const kickerActive = laneIsActive(pathname, kicker.href);
  const scrollRef = useCenterActiveInScrollRow<HTMLElement>(`${preset}:${pathname}`);

  return (
    <nav
      id={id ?? `${preset}-ecosystem`}
      ref={scrollRef}
      aria-label="Ecosystem shortcuts"
      className="v4-subtab-row my-3 w-full max-w-full"
    >
      <Link
        href={kicker.href}
        className={cn("v4-subtab gap-1.5 text-xs sm:text-[13px]", kickerActive && "v4-subtab--active")}
      >
        <KickerIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
        {kicker.label}
      </Link>
      {lanes.map((lane) => {
        const Icon = lane.icon;
        const active = laneIsActive(pathname, lane.href);
        return (
          <Link
            key={lane.label}
            href={lane.href}
            className={cn("v4-subtab gap-1.5 text-xs sm:text-[13px]", active && "v4-subtab--active")}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
            {lane.label}
          </Link>
        );
      })}
    </nav>
  );
}
