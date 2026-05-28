"use client";

import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

import { UI_LANG_COOKIE, UI_LANG_STORAGE_KEY, type UiLanguage } from "@/lib/ui-language";

interface UiLanguageContextValue {
  language: UiLanguage;
  setLanguage: (next: UiLanguage) => void;
}

const UiLanguageContext = createContext<UiLanguageContextValue>({
  language: "en",
  setLanguage: () => undefined,
});

/** English-only UI — clears legacy SK preference from cookie/storage. */
function enforceEnglishOnly(): void {
  if (typeof document !== "undefined") {
    document.cookie = `${UI_LANG_COOKIE}=en; Path=/; Max-Age=31536000; SameSite=Lax`;
    document.documentElement.lang = "en";
  }
  if (typeof window !== "undefined") {
    window.localStorage.setItem(UI_LANG_STORAGE_KEY, "en");
  }
}

export function UiLanguageProvider({ children }: { children: ReactNode }): ReactNode {
  useEffect(() => {
    enforceEnglishOnly();
  }, []);

  const value = useMemo<UiLanguageContextValue>(
    () => ({
      language: "en",
      setLanguage: () => undefined,
    }),
    [],
  );

  return <UiLanguageContext.Provider value={value}>{children}</UiLanguageContext.Provider>;
}

export function useUiLanguage(): UiLanguageContextValue {
  return useContext(UiLanguageContext);
}
