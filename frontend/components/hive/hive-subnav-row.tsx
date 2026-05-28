"use client";

import { Reorder } from "framer-motion";
import { GripVertical, Lock, Plus, Settings2, Unlock, X } from "lucide-react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, type KeyboardEvent, type ReactNode } from "react";
import { toast } from "sonner";

import { handleHorizontalNavKeydown } from "@/lib/hive-a11y";
import { useCenterActiveInScrollRow } from "@/lib/hooks/use-center-active-in-scroll-row";
import { useSubnavOrder } from "@/lib/hooks/use-subnav-order";
import { useSubnavVisibility } from "@/lib/hooks/use-subnav-visibility";
import { cn } from "@/lib/utils";

export interface HiveSubnavItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  badge?: number | string;
  hidden?: boolean;
  href?: string;
}

interface HiveSubnavRowProps {
  items: HiveSubnavItem[];
  activeId: string;
  onChange: (id: string) => void;
  ariaLabel: string;
  /** When set, enables lock/unlock gear, persisted reorder, and section disable toggles. */
  menuKey?: string;
  trailing?: ReactNode;
}

function SubnavLockGear({
  unlocked,
  onToggle,
  onReset,
}: {
  unlocked: boolean;
  onToggle: () => void;
  onReset: () => void;
}) {
  return (
    <span className="ml-auto flex shrink-0 items-center gap-1 pl-1">
      {unlocked ? (
        <button
          type="button"
          className="hive-subnav-gear hive-subnav-gear--unlock"
          aria-label="Reset tab order"
          title="Reset to default order"
          onClick={onReset}
        >
          ↺
        </button>
      ) : null}
      <button
        type="button"
        className={cn("hive-subnav-gear", unlocked && "hive-subnav-gear--active")}
        aria-label={unlocked ? "Lock and save tab order" : "Unlock to drag-reorder tabs"}
        aria-pressed={unlocked}
        title={unlocked ? "Lock and save order" : "Unlock — drag tabs to reorder, then lock to save"}
        onClick={onToggle}
      >
        {unlocked ? <Unlock className="h-3.5 w-3.5" aria-hidden /> : <Settings2 className="h-3.5 w-3.5" aria-hidden />}
      </button>
    </span>
  );
}

function SubnavTabContent({ item }: { item: HiveSubnavItem }) {
  const Icon = item.icon;
  return (
    <>
      {Icon ? <Icon className="h-3.5 w-3.5" aria-hidden /> : null}
      {item.label}
      {item.badge !== undefined ? (
        <span className="rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[10px]">{item.badge}</span>
      ) : null}
    </>
  );
}

function SubnavSectionToggle({
  disabled,
  canDisable,
  onDisable,
  onEnable,
}: {
  disabled: boolean;
  canDisable: boolean;
  onDisable: () => void;
  onEnable: () => void;
}) {
  if (disabled) {
    return (
      <button
        type="button"
        className="hive-subnav-restore"
        aria-label="Enable section"
        title="Enable section"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onEnable();
        }}
      >
        <Plus className="h-2.5 w-2.5" aria-hidden strokeWidth={3} />
      </button>
    );
  }

  if (!canDisable) {
    return null;
  }

  return (
    <button
      type="button"
      className="hive-subnav-dismiss"
      aria-label="Disable section"
      title="Disable section — stays offline until re-enabled"
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onDisable();
      }}
    >
      <X className="h-2.5 w-2.5" aria-hidden strokeWidth={2.5} />
    </button>
  );
}

function SubnavTabShell({
  item,
  active,
  disabled,
  canDisable,
  showToggle,
  onDisable,
  onEnable,
  onSelect,
  unlocked,
}: {
  item: HiveSubnavItem;
  active: boolean;
  disabled: boolean;
  canDisable: boolean;
  showToggle: boolean;
  onDisable: () => void;
  onEnable: () => void;
  onSelect: () => void;
  unlocked: boolean;
}) {
  const tabClass = cn(
    "v4-subtab shrink-0 gap-2",
    active && !disabled && "v4-subtab--active",
    disabled && "v4-subtab--disabled",
    unlocked && !disabled && "v4-subtab--draggable",
  );

  const inner = (
    <>
      {unlocked && !disabled ? (
        <GripVertical className="h-3.5 w-3.5 shrink-0 text-pollen/70" aria-hidden />
      ) : null}
      <SubnavTabContent item={item} />
    </>
  );

  return (
    <div className={cn("hive-subnav-tab-shell", disabled && "hive-subnav-tab-shell--disabled")}>
      {showToggle ? (
        <SubnavSectionToggle
          disabled={disabled}
          canDisable={canDisable}
          onDisable={onDisable}
          onEnable={onEnable}
        />
      ) : null}
      {disabled ? (
        <span className={tabClass} aria-disabled="true">
          {inner}
        </span>
      ) : item.href ? (
        <Link
          href={item.href}
          prefetch
          className={tabClass}
          onClick={onSelect}
          aria-current={active ? "page" : undefined}
          data-hive-subnav-tab
          data-hive-subnav-id={item.id}
        >
          {inner}
        </Link>
      ) : (
        <button
          type="button"
          className={tabClass}
          onClick={onSelect}
          aria-current={active ? "page" : undefined}
          data-hive-subnav-tab
          data-hive-subnav-id={item.id}
        >
          {inner}
        </button>
      )}
    </div>
  );
}

/** Single pill row with optional lock/reorder gear at the end. */
export function HiveSubnavRow({
  items,
  activeId,
  onChange,
  ariaLabel,
  menuKey,
  trailing,
}: HiveSubnavRowProps) {
  const visible = useMemo(() => items.filter((item) => !item.hidden), [items]);
  const defaultIds = useMemo(() => visible.map((item) => item.id), [visible]);
  const { orderedItems, unlocked, setUnlocked, reorderItems, commitOrder, resetOrder } = useSubnavOrder(
    menuKey,
    visible,
  );
  const visibility = useSubnavVisibility(menuKey, defaultIds);
  const scrollRef = useCenterActiveInScrollRow<HTMLElement>(unlocked ? "reorder-mode" : activeId);

  const displayItems = useMemo(() => {
    if (!menuKey || unlocked) {
      return orderedItems;
    }
    return orderedItems.filter((item) => visibility.enabledIds.includes(item.id));
  }, [menuKey, orderedItems, unlocked, visibility.enabledIds]);

  useEffect(() => {
    if (!menuKey || !visibility.isDisabled(activeId)) {
      return;
    }
    const next = visibility.enabledIds[0];
    if (next && next !== activeId) {
      onChange(next);
    }
  }, [activeId, menuKey, onChange, visibility]);

  const handleLockToggle = useCallback(() => {
    if (unlocked) {
      commitOrder();
      setUnlocked(false);
      return;
    }
    setUnlocked(true);
  }, [commitOrder, setUnlocked, unlocked]);

  const handleReset = useCallback(() => {
    resetOrder();
    setUnlocked(false);
  }, [resetOrder, setUnlocked]);

  const handleReorder = useCallback(
    (next: HiveSubnavItem[]) => {
      reorderItems(next);
    },
    [reorderItems],
  );

  const handleDisable = useCallback(
    (id: string) => {
      if (!menuKey) {
        return;
      }
      const next = visibility.enabledIds.find((row) => row !== id);
      const ok = visibility.disable(id);
      if (!ok) {
        toast.message("At least one section must stay enabled.");
        return;
      }
      if (id === activeId && next) {
        onChange(next);
      }
    },
    [activeId, menuKey, onChange, visibility],
  );

  const handleEnable = useCallback(
    (id: string) => {
      visibility.enable(id);
    },
    [visibility],
  );

  const handleNavKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      if (unlocked) {
        return;
      }
      handleHorizontalNavKeydown(event.nativeEvent, event.currentTarget, (tab) => {
        const id = tab.getAttribute("data-hive-subnav-id");
        if (id) {
          onChange(id);
        }
      });
    },
    [onChange, unlocked],
  );

  if (visible.length === 0) {
    return null;
  }

  const renderTab = (item: HiveSubnavItem, dragWrap?: (node: ReactNode) => ReactNode) => {
    const disabled = menuKey ? visibility.isDisabled(item.id) : false;
    const active = item.id === activeId;
    const shell = (
      <SubnavTabShell
        item={item}
        active={active}
        disabled={disabled}
        canDisable={visibility.canDisable}
        showToggle={Boolean(menuKey && unlocked)}
        onDisable={() => handleDisable(item.id)}
        onEnable={() => handleEnable(item.id)}
        onSelect={() => onChange(item.id)}
        unlocked={unlocked}
      />
    );
    return dragWrap ? dragWrap(shell) : <div key={item.id} className="flex shrink-0 items-center">{shell}</div>;
  };

  return (
    <nav
      ref={scrollRef}
      aria-label={ariaLabel}
      className={cn("v4-subtab-row w-full max-w-full", unlocked && "v4-subtab-row--unlocked")}
      onKeyDown={handleNavKeyDown}
    >
      {unlocked ? (
        <Reorder.Group
          axis="x"
          layoutScroll
          values={displayItems}
          onReorder={handleReorder}
          className="flex min-w-0 flex-1 flex-nowrap items-center gap-1"
        >
          {displayItems.map((item) =>
            renderTab(item, (shell) => (
              <Reorder.Item
                key={item.id}
                value={item}
                className="hive-subnav-drag-item flex shrink-0 items-center"
                whileDrag={{ scale: 1.04, zIndex: 20 }}
              >
                {shell}
              </Reorder.Item>
            )),
          )}
        </Reorder.Group>
      ) : (
        displayItems.map((item) => renderTab(item))
      )}
      {trailing}
      {menuKey ? (
        <SubnavLockGear unlocked={unlocked} onToggle={handleLockToggle} onReset={handleReset} />
      ) : null}
      {unlocked ? (
        <span className="hidden items-center gap-1 text-[10px] uppercase tracking-wider text-pollen sm:inline-flex">
          <Lock className="h-3 w-3" aria-hidden />
          {visibility.disabledIds.size > 0 ? "Offline sections · drag to reorder" : "Drag to reorder"}
        </span>
      ) : null}
    </nav>
  );
}
