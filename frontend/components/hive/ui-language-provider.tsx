"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { coerceUiLanguage, DEFAULT_UI_LANGUAGE, UI_LANG_COOKIE, UI_LANG_STORAGE_KEY, type UiLanguage } from "@/lib/ui-language";

interface UiLanguageContextValue {
  language: UiLanguage;
  setLanguage: (next: UiLanguage) => void;
}

const UiLanguageContext = createContext<UiLanguageContextValue>({
  language: DEFAULT_UI_LANGUAGE,
  setLanguage: () => undefined,
});

function readLanguageFromBrowser(): UiLanguage {
  if (typeof document === "undefined") {
    return DEFAULT_UI_LANGUAGE;
  }
  const cookieMatch = document.cookie.match(new RegExp(`(?:^|; )${UI_LANG_COOKIE}=([^;]+)`));
  const cookieValue = cookieMatch ? decodeURIComponent(cookieMatch[1] ?? "") : null;
  if (cookieValue) {
    return coerceUiLanguage(cookieValue);
  }
  const storageValue = typeof window !== "undefined" ? window.localStorage.getItem(UI_LANG_STORAGE_KEY) : null;
  return coerceUiLanguage(storageValue);
}

function persistLanguage(next: UiLanguage): void {
  if (typeof document !== "undefined") {
    document.cookie = `${UI_LANG_COOKIE}=${encodeURIComponent(next)}; Path=/; Max-Age=31536000; SameSite=Lax`;
    document.documentElement.lang = next;
  }
  if (typeof window !== "undefined") {
    window.localStorage.setItem(UI_LANG_STORAGE_KEY, next);
  }
}

export function UiLanguageProvider({ children }: { children: ReactNode }): ReactNode {
  const [language, setLanguageState] = useState<UiLanguage>(DEFAULT_UI_LANGUAGE);

  useEffect(() => {
    const initial = readLanguageFromBrowser();
    setLanguageState(initial);
    persistLanguage(initial);
  }, []);

  const setLanguage = (next: UiLanguage) => {
    const safe = coerceUiLanguage(next);
    setLanguageState(safe);
    persistLanguage(safe);
  };

  const value = useMemo<UiLanguageContextValue>(() => ({ language, setLanguage }), [language]);
  return (
    <UiLanguageContext.Provider value={value}>
      {/* Remount on language change so stale DOM translations cannot persist. */}
      <div key={language} className="contents">
        {children}
      </div>
    </UiLanguageContext.Provider>
  );
}

export function useUiLanguage(): UiLanguageContextValue {
  return useContext(UiLanguageContext);
}
