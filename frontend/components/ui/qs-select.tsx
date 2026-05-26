"use client";

import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

export interface QsSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface QsSelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: readonly QsSelectOption[];
  disabled?: boolean;
  /** Applied to the trigger button only (not a duplicate wrapper shell). */
  className?: string;
  id?: string;
  "aria-label"?: string;
  placeholder?: string;
}

interface MenuCoords {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
  placement: "bottom" | "top";
}

const MENU_GAP = 6;
const MENU_MAX_HEIGHT = 280;
const OPEN_MS = 40;

export function QsSelect({
  value,
  onValueChange,
  options,
  disabled = false,
  className,
  id,
  "aria-label": ariaLabel,
  placeholder = "Select…",
}: QsSelectProps): JSX.Element {
  const listboxId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [coords, setCoords] = useState<MenuCoords>({
    top: 0,
    left: 0,
    width: 0,
    maxHeight: MENU_MAX_HEIGHT,
    placement: "bottom",
  });
  const [highlightIndex, setHighlightIndex] = useState(0);

  const enabledOptions = options.filter((row) => !row.disabled);
  const selected = options.find((row) => row.value === value) ?? null;
  const selectedIndex = Math.max(
    0,
    enabledOptions.findIndex((row) => row.value === value),
  );

  const updateCoords = useCallback((): void => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }
    const rect = trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - MENU_GAP;
    const spaceAbove = rect.top - MENU_GAP;
    const placement = spaceBelow >= 160 || spaceBelow >= spaceAbove ? "bottom" : "top";
    const maxHeight = Math.min(MENU_MAX_HEIGHT, placement === "bottom" ? spaceBelow - 8 : spaceAbove - 8);

    setCoords({
      top: placement === "bottom" ? rect.bottom + MENU_GAP : rect.top - MENU_GAP,
      left: rect.left,
      width: rect.width,
      maxHeight: Math.max(120, maxHeight),
      placement,
    });
  }, []);

  const closeMenu = useCallback((): void => {
    setVisible(false);
    window.setTimeout(() => setOpen(false), OPEN_MS);
  }, []);

  const openMenu = useCallback((): void => {
    if (disabled) {
      return;
    }
    setHighlightIndex(selectedIndex >= 0 ? selectedIndex : 0);
    setOpen(true);
  }, [disabled, selectedIndex]);

  const chooseOption = useCallback(
    (nextValue: string): void => {
      onValueChange(nextValue);
      closeMenu();
      triggerRef.current?.focus();
    },
    [closeMenu, onValueChange],
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      setVisible(false);
      return;
    }
    updateCoords();
    const frame = window.requestAnimationFrame(() => setVisible(true));
    return () => window.cancelAnimationFrame(frame);
  }, [open, updateCoords]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onScrollOrResize = (): void => updateCoords();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open, updateCoords]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: MouseEvent): void => {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) {
        return;
      }
      closeMenu();
    };
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu();
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [closeMenu, open]);

  const onTriggerKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>): void => {
    if (disabled) {
      return;
    }
    if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (!open) {
        openMenu();
      }
    }
    if (event.key === "ArrowUp" && !open) {
      event.preventDefault();
      openMenu();
    }
  };

  const onPanelKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>): void => {
    if (!enabledOptions.length) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightIndex((idx) => (idx + 1) % enabledOptions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightIndex((idx) => (idx - 1 + enabledOptions.length) % enabledOptions.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      setHighlightIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setHighlightIndex(enabledOptions.length - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const row = enabledOptions[highlightIndex];
      if (row) {
        chooseOption(row.value);
      }
    } else if (event.key === "Tab") {
      closeMenu();
    }
  };

  const menu =
    open && mounted
      ? createPortal(
          <div
            ref={panelRef}
            id={listboxId}
            role="listbox"
            aria-label={ariaLabel}
            tabIndex={-1}
            className={cn(
              "qs-select-menu",
              visible && "qs-select-menu--open",
              coords.placement === "top" && "qs-select-menu--above",
            )}
            style={{
              position: "fixed",
              top: coords.placement === "bottom" ? coords.top : undefined,
              bottom: coords.placement === "top" ? window.innerHeight - coords.top : undefined,
              left: coords.left,
              width: coords.width,
              maxHeight: coords.maxHeight,
              zIndex: 9999,
            }}
            onKeyDown={onPanelKeyDown}
          >
            <div className="qs-select-menu-scroll">
              {options.map((option) => {
                const active = option.value === value;
                const highlighted =
                  enabledOptions[highlightIndex]?.value === option.value && !option.disabled;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    aria-selected={active}
                    disabled={option.disabled}
                    className={cn(
                      "qs-select-option",
                      active && "qs-select-option--active",
                      highlighted && "qs-select-option--highlight",
                    )}
                    onMouseEnter={() => {
                      const idx = enabledOptions.findIndex((row) => row.value === option.value);
                      if (idx >= 0) {
                        setHighlightIndex(idx);
                      }
                    }}
                    onClick={() => {
                      if (!option.disabled) {
                        chooseOption(option.value);
                      }
                    }}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>,
          document.body,
        )
      : null;

  return (
    <div className="qs-select">
      <button
        ref={triggerRef}
        id={id}
        type="button"
        disabled={disabled}
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        className={cn("qs-select-trigger", className, open && "qs-select-trigger--open")}
        onClick={() => {
          if (open) {
            closeMenu();
          } else {
            openMenu();
          }
        }}
        onKeyDown={onTriggerKeyDown}
      >
        <span className="qs-select-trigger-label">{selected?.label ?? placeholder}</span>
      </button>
      {menu}
    </div>
  );
}
