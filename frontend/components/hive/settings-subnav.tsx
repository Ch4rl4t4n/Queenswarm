"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SETTINGS_NAV_SECTIONS } from "@/lib/settings-nav";
import { cn } from "@/lib/utils";

export function SettingsSubnav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Settings sections" className="v4-subtab-row w-full max-w-full">
      {SETTINGS_NAV_SECTIONS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link key={href} href={href} className={cn("v4-subtab", active && "v4-subtab--active")}>
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
