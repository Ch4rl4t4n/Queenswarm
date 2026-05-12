"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const SECTIONS: { href: string; label: string }[] = [
  { href: "/settings/profile", label: "Profile" },
  { href: "/settings/security", label: "Security · 2FA" },
  { href: "/settings/api-keys", label: "API keys" },
  { href: "/settings/llm-keys", label: "LLM keys" },
  { href: "/settings/notifications", label: "Notifications" },
  { href: "/settings/appearance", label: "Appearance" },
  { href: "/settings/billing", label: "Billing" },
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
              "shrink-0 rounded-xl px-3 py-2.5 font-[family-name:var(--font-inter)] text-sm transition lg:block",
              active ? "bg-[rgb(61_53_38/0.92)] text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.3)]" : "text-zinc-400 hover:bg-white/[0.04] hover:text-pollen",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
