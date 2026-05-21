"use client";

import { ChevronUp } from "lucide-react";
import Link from "next/link";
import { useCallback, useId, useState } from "react";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { HIVE_SIDEBAR_SHORTCUTS } from "@/lib/hive-sidebar-shortcuts";
import { localizePhrase } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

interface SidebarShortcutsProps {
  className?: string;
  onNavigate?: () => void;
}

/** Collapsible Ctrl+letter drawer — expands upward from footer, no inner scroll. */
export function SidebarShortcuts({ className, onNavigate }: SidebarShortcutsProps) {
  const { language } = useUiLanguage();
  const [open, setOpen] = useState(false);
  const panelId = useId();

  const toggle = useCallback(() => {
    setOpen((v) => !v);
  }, []);

  const title = localizePhrase(language, { en: "Shortcuts", sk: "Skratky" });

  return (
    <section
      className={cn("hive-shortcuts-drawer", open && "hive-shortcuts-drawer--open", className)}
      aria-label={localizePhrase(language, { en: "Keyboard shortcuts", sk: "Klávesové skratky" })}
    >
      <button
        type="button"
        className="hive-shortcuts-drawer-trigger"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
      >
        <span className="hive-shortcuts-drawer-trigger-label">{title}</span>
        <ChevronUp className={cn("hive-shortcuts-drawer-chevron", open && "hive-shortcuts-drawer-chevron--open")} aria-hidden />
      </button>

      {open ? (
        <div id={panelId} className="hive-shortcuts-drawer-panel hive-shortcuts-drawer-panel--open">
          <div className="hive-shortcuts-drawer-panel-inner">
            <div className="hive-shortcuts-drawer-grid">
              {HIVE_SIDEBAR_SHORTCUTS.map((row) => (
                <Link
                  key={row.href + row.key}
                  href={row.href}
                  prefetch={false}
                  title={localizePhrase(language, row.label)}
                  className="hive-shortcut-bubble"
                  onClick={() => {
                    onNavigate?.();
                    setOpen(false);
                  }}
                >
                  <kbd className="hive-shortcut-bubble-key">Ctrl+{row.key.toUpperCase()}</kbd>
                  <span className="hive-shortcut-bubble-label">{localizePhrase(language, row.label)}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
