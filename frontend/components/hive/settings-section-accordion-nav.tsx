"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { SettingsNavSection } from "@/lib/settings-nav";
import { isSettingsNavSectionActive } from "@/lib/settings-panel-registry";
import { v4SectionToneHeader, v4SectionToneShell } from "@/lib/v4-section-tones";
import { cn } from "@/lib/utils";

interface SettingsSectionAccordionNavProps {
  sections: SettingsNavSection[];
  ariaLabel: string;
}

/** Vertical accordion-style settings section nav (platform matrix header pattern). */
export function SettingsSectionAccordionNav({ sections, ariaLabel }: SettingsSectionAccordionNavProps) {
  const pathname = usePathname();

  if (sections.length === 0) {
    return null;
  }

  return (
    <nav aria-label={ariaLabel} className="v4-settings-accordion-nav">
      {sections.map((section) => {
        const active = isSettingsNavSectionActive(pathname, section.href);
        const Icon = section.icon;
        const tone = section.tone ?? "zinc";
        const hint = section.hint ?? section.label;

        return (
          <Link
            key={section.href}
            href={section.href}
            prefetch
            aria-current={active ? "page" : undefined}
            className={cn(
              "v4-settings-accordion-row border",
              v4SectionToneShell(tone),
              active && "v4-settings-accordion-row--active",
            )}
          >
            <span className="flex min-w-0 flex-1 items-start gap-3">
              {Icon ? (
                <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", v4SectionToneHeader(tone))} aria-hidden />
              ) : null}
              <span className="min-w-0 flex-1">
                <span className={cn("block truncate text-sm font-semibold", v4SectionToneHeader(tone))}>
                  {section.label}
                </span>
                <span className="mt-0.5 block truncate text-xs text-(--qs-text-3)">{hint}</span>
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-3 text-xs tabular-nums text-(--qs-text-3)">
              <span className="hidden sm:inline">{section.shortLabel ?? "Open"}</span>
              <span
                className={cn("v4-panel-collapsible-chevron", active && "v4-panel-collapsible-chevron--open")}
                aria-hidden
              >
                <ChevronDown className="h-4 w-4" />
              </span>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
