"use client";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { code: "en" as const, label: "ENG" },
  { code: "sk" as const, label: "SVK" },
] as const;

interface SettingsLanguageSwitchProps {
  className?: string;
  /** Compact inline pill — does not stretch full row width on mobile. */
  compact?: boolean;
}

/** Matches Settings subnav active pill (Security · 2FA) — gold gradient + dark label. */
export function SettingsLanguageSwitch({ className, compact = false }: SettingsLanguageSwitchProps) {
  const { language, setLanguage } = useUiLanguage();

  return (
    <div
      className={cn(compact ? "v4-lang-switch" : "v4-subtab-row", className)}
      role="group"
      aria-label="Language"
    >
      {OPTIONS.map((opt) => {
        const active = language === opt.code;
        return (
          <button
            key={opt.code}
            type="button"
            onClick={() => setLanguage(opt.code)}
            className={cn(
              "v4-subtab justify-center text-xs font-semibold",
              compact ? "min-w-[2.75rem] px-2.5 py-1" : "min-w-[4.5rem] px-4 py-1.5",
              active && "v4-subtab--active",
            )}
            aria-pressed={active}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
