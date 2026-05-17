"use client";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { cn } from "@/lib/utils";

export function SettingsLanguageSwitch() {
  const { language, setLanguage } = useUiLanguage();

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">Language</span>
      <div className="inline-flex rounded-xl border border-cyan/25 bg-black/35 p-1">
        <button
          type="button"
          onClick={() => setLanguage("en")}
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-semibold transition",
            language === "en" ? "bg-cyan/20 text-cyan" : "text-zinc-300 hover:text-zinc-100",
          )}
          aria-pressed={language === "en"}
        >
          ENG
        </button>
        <button
          type="button"
          onClick={() => setLanguage("sk")}
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-semibold transition",
            language === "sk" ? "bg-cyan/20 text-cyan" : "text-zinc-300 hover:text-zinc-100",
          )}
          aria-pressed={language === "sk"}
        >
          SVK
        </button>
      </div>
    </div>
  );
}
