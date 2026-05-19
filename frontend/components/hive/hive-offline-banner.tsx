"use client";

import { WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { localizePhrase } from "@/lib/ui-copy";

/** Sticky offline strip — mobile/tablet only (`lg:hidden`). */
export function HiveOfflineBanner(): JSX.Element | null {
  const { language } = useUiLanguage();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const sync = (): void => setOffline(!navigator.onLine);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  if (!offline) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="hive-offline-banner fixed inset-x-0 top-0 z-[200] flex items-center justify-center gap-2 border-b border-magenta/40 bg-[#1a0814]/95 px-4 py-2 text-center font-[family-name:var(--font-poppins)] text-xs text-magenta backdrop-blur-md lg:hidden"
      style={{ paddingTop: "calc(0.5rem + env(safe-area-inset-top, 0px))" }}
    >
      <WifiOff className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        {localizePhrase(language, {
          en: "You are offline — cached shell only. API calls resume when connected.",
          sk: "Ste offline — len cache shell. API sa obnoví po pripojení.",
        })}
      </span>
    </div>
  );
}
