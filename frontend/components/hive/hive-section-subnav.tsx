"use client";

import type { ReactNode } from "react";

import { HiveSubnavStack } from "@/components/hive/hive-subnav-stack";
import { HiveSubnavRow, type HiveSubnavItem } from "@/components/hive/hive-subnav-row";

export type { HiveSubnavItem };

interface HiveSectionSubnavProps {
  primary: HiveSubnavItem[];
  secondary?: HiveSubnavItem[];
  tertiary?: HiveSubnavItem[];
  activePrimary: string;
  activeSecondary?: string;
  activeTertiary?: string;
  onPrimaryChange: (id: string) => void;
  onSecondaryChange?: (id: string) => void;
  onTertiaryChange?: (id: string) => void;
  primaryAriaLabel?: string;
  secondaryAriaLabel?: string;
  tertiaryAriaLabel?: string;
  trailingPrimary?: ReactNode;
  /** localStorage key for primary row order */
  primaryMenuKey?: string;
  /** localStorage key for secondary row order */
  secondaryMenuKey?: string;
  /** localStorage key for tertiary row order */
  tertiaryMenuKey?: string;
}

/** Multi-tier pill sub-navigation — uniform gap between every row (see .hive-subnav-stack). */
export function HiveSectionSubnav({
  primary,
  secondary,
  tertiary,
  activePrimary,
  activeSecondary,
  activeTertiary,
  onPrimaryChange,
  onSecondaryChange,
  onTertiaryChange,
  primaryAriaLabel = "Section navigation",
  secondaryAriaLabel = "Sub-section navigation",
  tertiaryAriaLabel = "Sub-sub-section navigation",
  trailingPrimary,
  primaryMenuKey,
  secondaryMenuKey,
  tertiaryMenuKey,
}: HiveSectionSubnavProps): JSX.Element {
  const showSecondary =
    secondary && secondary.length > 0 && activeSecondary && onSecondaryChange;
  const showTertiary = tertiary && tertiary.length > 0 && activeTertiary && onTertiaryChange;

  return (
    <HiveSubnavStack>
      <HiveSubnavRow
        items={primary}
        activeId={activePrimary}
        onChange={onPrimaryChange}
        ariaLabel={primaryAriaLabel}
        menuKey={primaryMenuKey}
        trailing={trailingPrimary}
      />
      {showSecondary ? (
        <HiveSubnavRow
          items={secondary}
          activeId={activeSecondary}
          onChange={onSecondaryChange}
          ariaLabel={secondaryAriaLabel}
          menuKey={secondaryMenuKey}
        />
      ) : null}
      {showTertiary ? (
        <HiveSubnavRow
          items={tertiary}
          activeId={activeTertiary}
          onChange={onTertiaryChange}
          ariaLabel={tertiaryAriaLabel}
          menuKey={tertiaryMenuKey}
        />
      ) : null}
    </HiveSubnavStack>
  );
}
