"use client";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { code: "en" as const, label: "ENG" },
  { code: "sk" as const, label: "SVK" },
] as const;

/** Matches Settings subnav active pill (Security · 2FA) — gold gradient + dark label. */
export function SettingsLanguageSwitch() {
  const { language, setLanguage } = useUiLanguage();

  return (
    <div className="v4-subtab-row" role="group" aria-label="Language">
      {OPTIONS.map((opt) => {
        const active = language === opt.code;
        return (
          <button
            key={opt.code}
            type="button"
            onClick={() => setLanguage(opt.code)}
            className={cn("v4-subtab min-w-[4.5rem] justify-center px-4 py-1.5 text-xs font-semibold", active && "v4-subtab--active")}
            aria-pressed={active}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
