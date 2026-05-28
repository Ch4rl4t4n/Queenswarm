"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { V4Card } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

interface CollapsibleLazyPanelProps {
  readonly id?: string;
  readonly title: string;
  readonly hint?: string;
  readonly meta?: string;
  readonly hashKey?: string;
  /** When true, panel stays open with a static header (no collapse toggle). */
  readonly expanded?: boolean;
  /** Initial open state when collapsible (ignored when `expanded` is true). */
  readonly defaultOpen?: boolean;
  /** `card` = standalone V4Card; `embedded` = compact row inside a parent card. */
  readonly variant?: "card" | "embedded";
  readonly className?: string;
  readonly panelClassName?: string;
  readonly onOpenChange?: (open: boolean) => void;
  /** Legacy — prefer `lazyContent` so collapsed panels do not mount heavy trees. */
  readonly children?: ReactNode;
  /** Invoked only while expanded — keeps collapsed sections out of the React tree. */
  readonly lazyContent?: () => ReactNode;
}

/** Compact longitudinal bubble — expands to reveal heavy panels; pair lazy fetch with `onOpenChange`. */
export function CollapsibleLazyPanel({
  id,
  title,
  hint,
  meta,
  hashKey,
  variant = "card",
  className,
  panelClassName,
  onOpenChange,
  children,
  lazyContent,
  expanded = false,
  defaultOpen = false,
}: CollapsibleLazyPanelProps): JSX.Element {
  const [open, setOpen] = useState(expanded || defaultOpen);
  const panelId = id ? `${id}-panel` : undefined;

  useEffect(() => {
    if (expanded) {
      setOpen(true);
      onOpenChange?.(true);
      return;
    }
    if (!hashKey) {
      return;
    }
    const syncFromHash = (): void => {
      if (window.location.hash.replace(/^#/, "").trim() === hashKey) {
        setOpen(true);
        onOpenChange?.(true);
      }
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, [expanded, hashKey, onOpenChange]);

  function toggle(): void {
    if (expanded) {
      return;
    }
    setOpen((value) => {
      const next = !value;
      onOpenChange?.(next);
      return next;
    });
  }

  const trigger = expanded ? (
    <div className={cn("flex w-full min-w-0 items-center justify-between gap-3", variant === "card" ? "py-2.5" : "px-1 py-2.5")}>
      <span className="flex min-w-0 items-center gap-3">
        <span className="truncate text-sm font-semibold text-(--qs-text-1)">{title}</span>
        {hint ? (
          <span className="hidden truncate text-xs text-(--qs-text-3) sm:inline">{hint}</span>
        ) : null}
      </span>
      {meta ? <span className="shrink-0 text-xs tabular-nums text-(--qs-text-3)">{meta}</span> : null}
    </div>
  ) : (
    <button
      type="button"
      className={cn(
        "v4-panel-collapsible-trigger flex w-full min-w-0 items-center justify-between gap-3 text-left",
        variant === "card" ? "py-2.5" : "px-1 py-2.5",
      )}
      onClick={toggle}
      aria-expanded={open}
      aria-controls={panelId}
    >
      <span className="flex min-w-0 items-center gap-3">
        <span className="truncate text-sm font-semibold text-(--qs-text-1)">{title}</span>
        {hint ? (
          <span className="hidden truncate text-xs text-(--qs-text-3) sm:inline">{hint}</span>
        ) : null}
      </span>
      <span className="flex shrink-0 items-center gap-3 text-xs tabular-nums text-(--qs-text-3)">
        {meta ? <span>{meta}</span> : null}
        <span
          className={cn("v4-panel-collapsible-chevron", open && "v4-panel-collapsible-chevron--open")}
          aria-hidden
        >
          <ChevronDown className="h-4 w-4" />
        </span>
      </span>
    </button>
  );

  const resolvedBody = open || expanded ? (lazyContent ? lazyContent() : children) : null;

  const body =
    resolvedBody != null && panelId ? (
      <div id={panelId} className={cn(variant === "card" && "border-t border-(--qs-border) pt-4", panelClassName)}>
        {resolvedBody}
      </div>
    ) : resolvedBody != null ? (
      <div className={cn(variant === "card" && "border-t border-(--qs-border) pt-4", panelClassName)}>{resolvedBody}</div>
    ) : null;

  if (variant === "embedded") {
    return (
      <div id={id} className={cn("min-w-0", className)}>
        {trigger}
        {body}
      </div>
    );
  }

  return (
    <V4Card id={id} tight className={cn(!open && "overflow-hidden", className)}>
      {trigger}
      {body}
    </V4Card>
  );
}
