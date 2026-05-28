import type { UiLanguage } from "@/lib/ui-language";

/** Navigation and function names stay English regardless of UI language. */
export function localizeNavLabel(label: string, language?: UiLanguage): string {
  void language;
  return label;
}

/** Buttons, toasts, and chrome labels — always English. */
export function localizePhrase(_language: UiLanguage, copy: { en: string; sk: string }): string {
  return copy.en;
}

/** Section descriptions and manual prose — English only. */
export function localizeDescription(_language: UiLanguage, copy: { en: string; sk: string }): string {
  return copy.en;
}
