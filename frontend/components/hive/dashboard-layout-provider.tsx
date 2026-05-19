"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DASHBOARD_LAYOUT_DEFAULTS,
  readStoredDashboardLayoutFromBrowser,
  saveStoredDashboardLayoutFromBrowser,
  type DashboardLayoutPreferences,
  type DashboardSectionId,
} from "@/lib/dashboard-layout-preferences";

interface DashboardLayoutContextValue {
  layout: DashboardLayoutPreferences;
  isVisible: (id: DashboardSectionId) => boolean;
  setVisible: (id: DashboardSectionId, visible: boolean) => void;
  resetLayout: () => void;
}

interface DashboardSettingsContextValue {
  settingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
  toggleSettings: () => void;
}

const DashboardLayoutContext = createContext<DashboardLayoutContextValue | null>(null);
const DashboardSettingsContext = createContext<DashboardSettingsContextValue | null>(null);

/** Syncs body class so heavy dashboard canvas skips paint while layout flyout is open. */
function useDashboardSettingsBodyLock(open: boolean): void {
  useEffect(() => {
    document.documentElement.classList.toggle("dash-settings-open", open);
    return () => {
      document.documentElement.classList.remove("dash-settings-open");
    };
  }, [open]);
}

export function DashboardLayoutProvider({ children }: { children: ReactNode }) {
  const [layout, setLayout] = useState<DashboardLayoutPreferences>(DASHBOARD_LAYOUT_DEFAULTS);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    setLayout(readStoredDashboardLayoutFromBrowser());
  }, []);

  useDashboardSettingsBodyLock(settingsOpen);

  const persist = useCallback((next: DashboardLayoutPreferences) => {
    setLayout(next);
    saveStoredDashboardLayoutFromBrowser(next);
  }, []);

  const isVisible = useCallback((id: DashboardSectionId) => layout[id], [layout]);

  const setVisible = useCallback(
    (id: DashboardSectionId, visible: boolean) => {
      setLayout((prev) => {
        if (prev[id] === visible) {
          return prev;
        }
        const next = { ...prev, [id]: visible };
        saveStoredDashboardLayoutFromBrowser(next);
        return next;
      });
    },
    [],
  );

  const resetLayout = useCallback(() => {
    persist({ ...DASHBOARD_LAYOUT_DEFAULTS });
  }, [persist]);

  const layoutValue = useMemo<DashboardLayoutContextValue>(
    () => ({
      layout,
      isVisible,
      setVisible,
      resetLayout,
    }),
    [layout, isVisible, setVisible, resetLayout],
  );

  const settingsValue = useMemo<DashboardSettingsContextValue>(
    () => ({
      settingsOpen,
      openSettings: () => setSettingsOpen(true),
      closeSettings: () => setSettingsOpen(false),
      toggleSettings: () => setSettingsOpen((v) => !v),
    }),
    [settingsOpen],
  );

  return (
    <DashboardLayoutContext.Provider value={layoutValue}>
      <DashboardSettingsContext.Provider value={settingsValue}>{children}</DashboardSettingsContext.Provider>
    </DashboardLayoutContext.Provider>
  );
}

export function useDashboardLayout(): DashboardLayoutContextValue {
  const ctx = useContext(DashboardLayoutContext);
  if (!ctx) {
    throw new Error("useDashboardLayout must be used within DashboardLayoutProvider");
  }
  return ctx;
}

export function useDashboardSettings(): DashboardSettingsContextValue {
  const ctx = useContext(DashboardSettingsContext);
  if (!ctx) {
    throw new Error("useDashboardSettings must be used within DashboardLayoutProvider");
  }
  return ctx;
}

export function useDashboardSection(id: DashboardSectionId): boolean {
  const { layout } = useDashboardLayout();
  return layout[id];
}
