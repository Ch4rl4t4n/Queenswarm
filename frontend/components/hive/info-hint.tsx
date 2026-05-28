"use client";

import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";

import { HivePopoverShell } from "@/components/hive/hive-popover-shell";
import {
  resolveLocalizedDescription,
  resolveLocalizedLabel,
  resolveLocalizedStringList,
  type MaybeLocalizedString,
  type MaybeLocalizedStringList,
} from "@/lib/ui-language";
import { cn } from "@/lib/utils";

interface InfoHintProps {
  title: MaybeLocalizedString;
  description: MaybeLocalizedString;
  options?: MaybeLocalizedStringList;
  /** Deep link to full manual section, e.g. `/manual#bee-hotline`. */
  manualHref?: string;
  manualLabel?: string;
  className?: string;
}

/**
 * Small circular info icon with a portaled popup — escapes card overflow and stacks above all UI.
 */
export function InfoHint({
  title,
  description,
  options,
  manualHref,
  manualLabel = "Full manual →",
  className,
}: InfoHintProps): ReactNode {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  const titleText = resolveLocalizedLabel(title, "en");
  const descriptionText = resolveLocalizedDescription(description, "en");
  const optionItems = resolveLocalizedStringList(options, "en");
  const settingsOptionsLabel = "Configuration options";

  return (
    <>
      <span ref={wrapRef} className={cn("hive-inline-hint", className)}>
        <button
          ref={buttonRef}
          type="button"
          aria-label={`Info: ${titleText}`}
          aria-expanded={open}
          onClick={() => setOpen((prev) => !prev)}
          className="hive-inline-hint-trigger"
        >
          i
        </button>
      </span>
      <HivePopoverShell
        open={open}
        onClose={() => setOpen(false)}
        presentation="anchor"
        anchorRef={buttonRef}
        ignoreOutsideRefs={[wrapRef]}
        ariaLabel={titleText}
        panelClassName="hive-info-hint-panel"
        preferredWidth={320}
      >
        <strong className="hive-info-hint-panel__title">{titleText}</strong>
        <p className="hive-info-hint-panel__description">{descriptionText}</p>
        {optionItems?.length ? (
          <div className="hive-info-hint-panel__options">
            <span className="hive-info-hint-panel__options-label">{settingsOptionsLabel}</span>
            <ul className="hive-info-hint-panel__list">
              {optionItems.map((option) => (
                <li key={option}>{option}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {manualHref ? (
          <Link href={manualHref} className="hive-info-hint-panel__link" onClick={() => setOpen(false)}>
            {manualLabel}
          </Link>
        ) : null}
      </HivePopoverShell>
    </>
  );
}
