"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { resolveLocalizedString, resolveLocalizedStringList, type MaybeLocalizedString, type MaybeLocalizedStringList } from "@/lib/ui-language";
import { cn } from "@/lib/utils";

interface InfoHintProps {
  title: MaybeLocalizedString;
  description: MaybeLocalizedString;
  options?: MaybeLocalizedStringList;
  className?: string;
}

/**
 * Small circular info icon with an inline popup.
 * Used across sections to explain functionality and available settings.
 */
export function InfoHint({ title, description, options, className }: InfoHintProps): ReactNode {
  const { language } = useUiLanguage();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement | null>(null);
  const titleText = resolveLocalizedString(title, language);
  const descriptionText = resolveLocalizedString(description, language);
  const optionItems = resolveLocalizedStringList(options, language);
  const settingsOptionsLabel = language === "sk" ? "Možnosti nastavenia" : "Configuration options";

  useEffect(() => {
    if (!open) {
      return;
    }
    const onClickAway = (event: MouseEvent) => {
      if (!wrapRef.current) {
        return;
      }
      if (!wrapRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", onClickAway);
    return () => window.removeEventListener("mousedown", onClickAway);
  }, [open]);

  return (
    <span ref={wrapRef} className={cn("relative inline-flex", className)}>
      <button
        type="button"
        aria-label={`Info: ${titleText}`}
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-[color:var(--qs-border-2)] bg-[#0a1424] text-[11px] font-semibold text-cyan transition hover:border-[color:var(--qs-border-2)] hover:text-white"
      >
        i
      </button>
      {open ? (
        <span
          role="dialog"
          className="absolute right-0 top-7 z-50 w-[min(320px,85vw)] rounded-xl border border-[color:var(--qs-border-2)] bg-[#060c16] p-3 text-left shadow-[0_0_24px_rgba(0,255,255,0.16)]"
        >
          <strong className="block text-sm text-zinc-100">{titleText}</strong>
          <span className="mt-1 block text-xs leading-relaxed text-zinc-300">{descriptionText}</span>
          {optionItems?.length ? (
            <span className="mt-2 block">
              <span className="block text-[11px] uppercase tracking-[0.08em] text-zinc-500">{settingsOptionsLabel}</span>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-zinc-300">
                {optionItems.map((option) => (
                  <li key={option}>{option}</li>
                ))}
              </ul>
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}

