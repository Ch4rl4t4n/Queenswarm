"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { SectionTabBar, type SectionTab } from "./section-tab-bar";

export interface SectionWorkspaceProps {
  /** Sub-section menu bar entries. */
  tabs: SectionTab[];
  /** Active sub-section id. */
  active: string;
  /** Switch sub-section. */
  onSelect: (id: string) => void;
  /** Optional process-rail node rendered under the tab bar (workflow compass). */
  rail?: ReactNode;
  /** Optional controls aligned to the right of the tab bar. */
  toolbar?: ReactNode;
  /** Active sub-section content — the stacked, configurable/executable blocks. */
  children: ReactNode;
  /** Optional result slot rendered after the blocks (download / handoff). */
  result?: ReactNode;
  className?: string;
  ariaLabel?: string;
}

/**
 * Reusable section shell: sub-section menu bar + process rail + blocks + result.
 *
 * Implements the operator model (section -> sub-sections -> workflow -> result)
 * inside the canvas while the left sidebar keeps selecting the section. Mission
 * Control is the first consumer; other sections reuse the same primitive.
 */
export function SectionWorkspace({
  tabs,
  active,
  onSelect,
  rail,
  toolbar,
  children,
  result,
  className,
  ariaLabel,
}: SectionWorkspaceProps): JSX.Element {
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <SectionTabBar tabs={tabs} active={active} onSelect={onSelect} ariaLabel={ariaLabel} />
        {toolbar ? <div className="flex flex-wrap items-center gap-2">{toolbar}</div> : null}
      </div>
      {rail ?? null}
      {children}
      {result ?? null}
    </div>
  );
}
