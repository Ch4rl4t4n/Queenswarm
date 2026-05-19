"use client";

import { BellIcon, PanelLeftOpenIcon } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import type { DashboardSummary } from "@/lib/hive-types";
import { localizePhrase, localizeText } from "@/lib/ui-copy";
import { hiveMobileRouteMeta } from "@/lib/hive-mobile-meta";
import { cn } from "@/lib/utils";

interface HiveMobileHeaderProps {
  pathname: string;
  summary: DashboardSummary | null;
  className?: string;
  /** Opens primary navigation drawer (&lt; lg). */
  onOpenNav?: () => void;
}

function onlineLine(summary: DashboardSummary | null, language: "en" | "sk"): string {
  if (!summary?.agents?.by_status) {
    return language === "sk" ? "synchronizujem hive…" : "syncing hive…";
  }
  const total = summary.agents.total;
  let offlineErr = 0;
  for (const [k, v] of Object.entries(summary.agents.by_status)) {
    const u = k.toUpperCase();
    if (u === "OFFLINE" || u === "ERROR") offlineErr += v;
  }
  const online = Math.max(0, total - offlineErr);
  return total
    ? language === "sk"
      ? `${online} agentov online`
      : `${online} agents online`
    : language === "sk"
      ? "hive sa zahrieva…"
      : "hive warming…";
}

/** Mobile / tablet sticky strip — nav drawer + context subtitle. */
export function HiveMobileHeader({ pathname, summary, className, onOpenNav }: HiveMobileHeaderProps) {
  const { language } = useUiLanguage();
  const meta = useMemo(() => hiveMobileRouteMeta(pathname), [pathname]);
  const contextualLine = useMemo(() => {
    if (pathname === "/") {
      return onlineLine(summary, language);
    }
    if (pathname.startsWith("/ballroom") || pathname === "/ballroom") {
      return localizePhrase(language, { en: "Voice + transcript", sk: "Hlas + prepis" });
    }
    return meta.staticSubtitle ?? "";
  }, [pathname, summary, meta.staticSubtitle, language]);

  return (
    <header
      className={cn(
        "sticky top-0 z-[45] flex items-start justify-between gap-3 border-b border-[color:var(--qs-border)] bg-[#0a0a0c]/95 px-4 py-4 backdrop-blur-lg lg:hidden",
        "pt-[calc(1rem+env(safe-area-inset-top,0px))]",
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 items-start gap-2">
        {onOpenNav ? (
          <button
            type="button"
            className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[color:var(--qs-border)] bg-black/55 text-pollen hover:border-[color:var(--qs-border-2)] touch-manipulation"
            aria-label={localizePhrase(language, { en: "Open navigation menu", sk: "Otvoriť navigáciu" })}
            onClick={onOpenNav}
          >
            <PanelLeftOpenIcon className="h-[22px] w-[22px]" aria-hidden />
          </button>
        ) : null}
        <Link
          href="/"
          className="flex min-w-0 flex-1 items-start gap-3"
          prefetch
          aria-label={localizePhrase(language, { en: "Go to dashboard", sk: "Prejsť na nástenku" })}
        >
          <span className="hive-hex mt-1 flex h-10 w-10 shrink-0 items-center justify-center border-[5px] border-black/55 bg-gradient-to-br from-pollen to-amber-600 shadow-[0_0_22px_rgb(255_184_0/0.52)] ring-[5px] ring-black/70">
            <span className="text-xs font-black text-black">Q</span>
          </span>
          <span className="min-w-0">
            <p className="font-[family-name:var(--font-poppins)] text-[11px] font-semibold uppercase tracking-[0.18em] text-pollen">
              {localizeText(meta.kicker, language)}
            </p>
            <p className="line-clamp-2 font-[family-name:var(--font-poppins)] text-xs text-muted-foreground">
              {localizeText(contextualLine, language)}
            </p>
          </span>
        </Link>
      </div>
      <Link
        href="/settings/notifications"
        aria-label={localizePhrase(language, { en: "Notifications", sk: "Notifikácie" })}
        className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[color:var(--qs-border)] bg-black/55 text-zinc-300 hover:border-[color:var(--qs-border-2)] hover:text-pollen touch-manipulation"
      >
        <BellIcon className="h-[18px] w-[18px]" aria-hidden />
      </Link>
    </header>
  );
}
