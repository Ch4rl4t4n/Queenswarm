"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const SECTIONS: { href: string; label: string }[] = [
  { href: "/settings/security", label: "Security · 2FA" },
  { href: "/settings/llm-keys", label: "LLM keys" },
  { href: "/settings/notifications", label: "Notifications" },
  { href: "/settings/api-keys", label: "API keys · external" },
];

export function SettingsSubnav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Settings sections"
      className={cn(
        "hive-scrollbar flex shrink-0 gap-2 overflow-x-auto whitespace-nowrap rounded-2xl border border-cyan/[0.12] bg-hive-card/80 p-2",
        "lg:w-[220px] lg:flex-col lg:gap-1 lg:overflow-visible lg:whitespace-normal",
      )}
    >
      {SECTIONS.map(({ href, label }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "qs-pill shrink-0 px-4 py-3 text-center transition lg:block lg:w-full",
              active && "qs-pill--active-amber",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
