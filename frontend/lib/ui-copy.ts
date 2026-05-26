import type { UiLanguage } from "@/lib/ui-language";

/** Navigation and function names stay English regardless of UI language. */
export function localizeNavLabel(label: string, _language?: UiLanguage): string {
  return label;
}

/** Buttons, toasts, and chrome labels — always English. */
export function localizePhrase(_language: UiLanguage, copy: { en: string; sk: string }): string {
  return copy.en;
}

/** Section descriptions and manual prose — Slovak when SVK is selected. */
export function localizeDescription(language: UiLanguage, copy: { en: string; sk: string }): string {
  return language === "sk" ? copy.sk : copy.en;
}
