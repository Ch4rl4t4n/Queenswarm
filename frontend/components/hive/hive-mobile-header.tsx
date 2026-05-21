"use client";

import { BellIcon, MenuIcon } from "lucide-react";
import Link from "next/link";

import { useHiveMobileHeaderTrailing } from "@/components/hive/hive-mobile-header-actions";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { useHiveNotificationBadge } from "@/lib/hooks/use-hive-notification-badge";
import type { DashboardSummary } from "@/lib/hive-types";
import { localizePhrase } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

interface HiveMobileHeaderProps {
  summary: DashboardSummary | null;
  className?: string;
  /** Opens primary navigation drawer (&lt; lg). */
  onOpenNav?: () => void;
}

/** Mobile / tablet sticky strip — hamburger nav + notification bell. */
export function HiveMobileHeader({ summary, className, onOpenNav }: HiveMobileHeaderProps) {
  const { language } = useUiLanguage();
  const badge = useHiveNotificationBadge(summary);
  const trailing = useHiveMobileHeaderTrailing();

  return (
    <header
      className={cn(
        "sticky top-0 z-[45] flex items-center justify-between gap-3 border-b border-[color:var(--qs-border)] bg-[#0a0a0c]/95 px-4 py-3 backdrop-blur-lg lg:hidden",
        "pt-[calc(0.75rem+env(safe-area-inset-top,0px))]",
        className,
      )}
    >
      {onOpenNav ? (
        <button
          type="button"
          className="hive-mobile-nav-trigger flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[color:var(--qs-border)] bg-black/55 text-pollen hover:border-pollen/40 touch-manipulation"
          aria-label={localizePhrase(language, { en: "Open navigation menu", sk: "Otvoriť navigáciu" })}
          onClick={onOpenNav}
        >
          <MenuIcon className="h-[22px] w-[22px]" strokeWidth={2.25} aria-hidden />
        </button>
      ) : (
        <span className="h-11 w-11 shrink-0" aria-hidden />
      )}

      <div className="flex shrink-0 items-center gap-2">
        {trailing}
        <Link
        href="/settings/notifications"
        aria-label={
          badge
            ? localizePhrase(language, {
                en: `Notifications (${badge} unread)`,
                sk: `Notifikácie (${badge} neprečítaných)`,
              })
            : localizePhrase(language, { en: "Notifications", sk: "Notifikácie" })
        }
        className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[color:var(--qs-border)] bg-black/55 text-zinc-300 hover:border-[color:var(--qs-border-2)] hover:text-pollen touch-manipulation"
      >
        <BellIcon className="h-[20px] w-[20px]" strokeWidth={2} aria-hidden />
        {badge ? (
          <span className="hive-mobile-notif-badge" aria-hidden>
            {badge}
          </span>
        ) : null}
      </Link>
      </div>
    </header>
  );
}
