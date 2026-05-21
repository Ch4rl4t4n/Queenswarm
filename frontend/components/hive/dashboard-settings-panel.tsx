"use client";

import { Settings2, X } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useDashboardLayout, useDashboardSettings } from "@/components/hive/dashboard-layout-provider";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import {
  DASHBOARD_SECTION_GROUPS,
  DASHBOARD_SECTIONS,
  type DashboardSectionId,
} from "@/lib/dashboard-layout-preferences";
import type { SectionDensity } from "@/lib/section-hub";
import { localizePhrase } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

interface DashboardSettingsTriggerProps {
  className?: string;
}

/** Gear on the Dashboard nav row — opens layout flyout. */
export function DashboardSettingsTrigger({ className }: DashboardSettingsTriggerProps) {
  const { settingsOpen, toggleSettings } = useDashboardSettings();
  const { language } = useUiLanguage();

  return (
    <button
      type="button"
      data-dash-settings-trigger
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] border border-transparent text-(--qs-text-3) transition",
        "hover:border-[rgba(253,185,39,0.28)] hover:bg-white/[0.05] hover:text-pollen",
        settingsOpen && "border-[rgba(253,185,39,0.35)] bg-[rgba(253,185,39,0.08)] text-pollen",
        className,
      )}
      aria-label={localizePhrase(language, { en: "Dashboard layout", sk: "Rozloženie dashboardu" })}
      aria-expanded={settingsOpen}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleSettings();
      }}
    >
      <Settings2 className="h-4 w-4" aria-hidden />
    </button>
  );
}

const SettingToggleRow = memo(function SettingToggleRow({
  sectionId,
  checked,
  onToggle,
  label,
  description,
}: {
  sectionId: DashboardSectionId;
  checked: boolean;
  onToggle: (id: DashboardSectionId, next: boolean) => void;
  label: string;
  description: string;
}) {
  const handleClick = useCallback(() => {
    onToggle(sectionId, !checked);
  }, [sectionId, checked, onToggle]);

  return (
    <label className="v4-dash-setting-row">
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium text-(--qs-text)">{label}</span>
        <span className="mt-0.5 block text-[11px] leading-snug text-(--qs-text-3)">{description}</span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        className={cn("v4-toggle", checked && "v4-toggle--on")}
        onClick={handleClick}
      >
        <span className="v4-toggle-knob" aria-hidden />
      </button>
    </label>
  );
});

/** Flyout panel — sections visible on Queen Dashboard (portaled to body). */
export function DashboardSettingsPanel() {
  const { language } = useUiLanguage();
  const { layout, setVisible, setDensity, density, resetLayout } = useDashboardLayout();
  const { settingsOpen, closeSettings } = useDashboardSettings();
  const panelRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!settingsOpen) {
      return undefined;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeSettings();
      }
    };
    const onPointer = (e: MouseEvent) => {
      const t = e.target as Node;
      if (panelRef.current?.contains(t)) {
        return;
      }
      const trigger = (e.target as HTMLElement | null)?.closest?.("[data-dash-settings-trigger]");
      if (trigger) {
        return;
      }
      closeSettings();
    };
    window.addEventListener("keydown", onKey);
    const timer = window.setTimeout(() => {
      window.addEventListener("mousedown", onPointer);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onPointer);
    };
  }, [settingsOpen, closeSettings]);

  const sectionsByGroup = useMemo(
    () =>
      DASHBOARD_SECTION_GROUPS.map((group) => ({
        group,
        sections: DASHBOARD_SECTIONS.filter((s) => s.group === group.id),
      })).filter((row) => row.sections.length > 0),
    [],
  );

  const handleToggle = useCallback(
    (id: DashboardSectionId, next: boolean) => {
      setVisible(id, next);
    },
    [setVisible],
  );

  if (!settingsOpen || !mounted) {
    return null;
  }

  return createPortal(
    <>
      <div className="v4-dash-settings-backdrop" aria-hidden onClick={closeSettings} />
      <div
        ref={panelRef}
        className="v4-dash-settings-panel v4-dash-settings-panel--open"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dash-settings-title"
      >
        <div className="v4-dash-settings-head">
          <div className="min-w-0">
            <h2 id="dash-settings-title" className="text-base font-semibold text-(--qs-text)">
              {localizePhrase(language, { en: "Dashboard layout", sk: "Rozloženie dashboardu" })}
            </h2>
            <p className="mt-0.5 text-xs text-(--qs-text-3)">
              {localizePhrase(language, {
                en: "Choose which blocks appear on Queen Dashboard.",
                sk: "Vyber, ktoré bloky sa zobrazia na Queen Dashboard.",
              })}
            </p>
          </div>
          <button
            type="button"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] border border-(--qs-border) text-(--qs-text-3) hover:text-pollen"
            aria-label={localizePhrase(language, { en: "Close", sk: "Zavrieť" })}
            onClick={closeSettings}
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="v4-dash-settings-body hive-scrollbar">
          {sectionsByGroup.map(({ group, sections }) => (
            <section key={group.id} className="v4-dash-settings-group">
              <h3 className="v4-label-kicker mb-3 text-(--qs-text-3)">
                {localizePhrase(language, group.label)}
              </h3>
              <div className="flex flex-col gap-2">
                {sections.map((section) => (
                  <SettingToggleRow
                    key={section.id}
                    sectionId={section.id}
                    checked={layout[section.id]}
                    onToggle={handleToggle}
                    label={localizePhrase(language, section.label)}
                    description={localizePhrase(language, section.description)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="v4-dash-settings-foot flex flex-col gap-3">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
              {localizePhrase(language, { en: "Section density", sk: "Hustota sekcií" })}
            </p>
            <div className="flex gap-2">
              {(["comfortable", "compact"] as SectionDensity[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={cn(
                    "flex-1 rounded-lg border px-3 py-1.5 text-xs capitalize",
                    density === mode
                      ? "border-pollen/60 bg-pollen/15 text-pollen"
                      : "border-(--qs-border) text-(--qs-text-3)",
                  )}
                  onClick={() => setDensity(mode)}
                >
                  {localizePhrase(language, mode === "compact" ? { en: "Compact", sk: "Kompaktné" } : { en: "Cozy", sk: "Pohodlné" })}
                </button>
              ))}
            </div>
          </div>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm w-full" onClick={resetLayout}>
            {localizePhrase(language, { en: "Reset to defaults", sk: "Obnoviť predvolené" })}
          </button>
        </div>
      </div>
    </>,
    document.body,
  );
}
