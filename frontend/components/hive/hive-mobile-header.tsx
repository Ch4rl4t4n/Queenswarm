"use client";

import { BellIcon, MenuIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { HiveBrandMark } from "@/components/hive/hive-brand-mark";
import { HiveMobileNotificationSheet } from "@/components/hive/hive-mobile-notification-sheet";
import { useHiveMobileHeaderTrailing } from "@/components/hive/hive-mobile-header-actions";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { useHiveNotificationBadge } from "@/lib/hooks/use-hive-notification-badge";
import type { DashboardSummary } from "@/lib/hive-types";
import { localizePhrase } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

interface HiveMobileHeaderProps {
  pathname: string;
  summary: DashboardSummary | null;
  className?: string;
  /** Opens primary navigation drawer (&lt; lg). */
  onOpenNav?: () => void;
  /** Notifies shell when mobile notification sheet opens/closes (hides FAB). */
  onNotificationsOpenChange?: (open: boolean) => void;
}

/** Mobile / tablet sticky strip — hamburger, home brand, notification bell. */
export function HiveMobileHeader({
  pathname: _pathname,
  summary,
  className,
  onOpenNav,
  onNotificationsOpenChange,
}: HiveMobileHeaderProps) {
  const { language } = useUiLanguage();
  const badge = useHiveNotificationBadge(summary);
  const trailing = useHiveMobileHeaderTrailing();
  const [notifOpen, setNotifOpen] = useState(false);

  useEffect(() => {
    onNotificationsOpenChange?.(notifOpen);
  }, [notifOpen, onNotificationsOpenChange]);

  return (
    <>
    <header
      data-testid="hive-mobile-header"
      className={cn(
        "sticky top-0 z-[45] border-b border-[color:var(--qs-border)] bg-[#0a0a0c]/95 px-3 py-3 backdrop-blur-lg lg:hidden",
        "pt-[calc(0.75rem+env(safe-area-inset-top,0px))]",
        className,
      )}
    >
      <div className="grid grid-cols-[2.75rem_minmax(0,1fr)_auto] items-center gap-2">
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

        <div className="hive-mobile-header-title min-w-0 px-1" data-testid="hive-mobile-header-title">
          <HiveBrandMark compact showTagline={false} className="hive-mobile-header-brand mx-auto w-auto" />
        </div>

        <div className="flex shrink-0 items-center gap-1.5 justify-self-end">
          {trailing}
          <button
            type="button"
            data-testid="hive-mobile-notifications-bell"
            aria-label={
              badge
                ? localizePhrase(language, {
                    en: `Notifications (${badge} unread)`,
                    sk: `Notifikácie (${badge} neprečítaných)`,
                  })
                : localizePhrase(language, { en: "Notifications", sk: "Notifikácie" })
            }
            className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[color:var(--qs-border)] bg-black/55 text-zinc-300 hover:border-[color:var(--qs-border-2)] hover:text-pollen touch-manipulation"
            onClick={() => setNotifOpen(true)}
          >
            <BellIcon className="h-[20px] w-[20px]" strokeWidth={2} aria-hidden />
            {badge ? (
              <span className="hive-mobile-notif-badge" aria-hidden>
                {badge}
              </span>
            ) : null}
          </button>
        </div>
      </div>
    </header>
    <HiveMobileNotificationSheet
      open={notifOpen}
      onClose={() => setNotifOpen(false)}
      summary={summary}
    />
    </>
  );
}
