export type UiLanguage = "en" | "sk";

export const UI_LANG_COOKIE = "qs_ui_lang";
export const UI_LANG_STORAGE_KEY = "qs.ui.language";
export const DEFAULT_UI_LANGUAGE: UiLanguage = "en";

export interface LocalizedString {
  en: string;
  sk: string;
}

export interface LocalizedStringList {
  en: string[];
  sk: string[];
}

export type MaybeLocalizedString = string | LocalizedString;
export type MaybeLocalizedStringList = string[] | LocalizedStringList;

export function coerceUiLanguage(value: string | null | undefined): UiLanguage {
  if (value === "sk") {
    return "sk";
  }
  return "en";
}

/** UI labels, nav, and function names — always English. */
export function resolveLocalizedLabel(value: MaybeLocalizedString, _lang: UiLanguage): string {
  if (typeof value === "string") {
    return value;
  }
  return value.en;
}

/** Section descriptions, hints, and manual prose — respects language toggle. */
export function resolveLocalizedDescription(value: MaybeLocalizedString, lang: UiLanguage): string {
  if (typeof value === "string") {
    return value;
  }
  return lang === "sk" ? value.sk : value.en;
}

/** @deprecated Use resolveLocalizedLabel or resolveLocalizedDescription explicitly. */
export function resolveLocalizedString(value: MaybeLocalizedString, lang: UiLanguage): string {
  return resolveLocalizedDescription(value, lang);
}

export function resolveLocalizedStringList(value: MaybeLocalizedStringList | undefined, lang: UiLanguage): string[] | undefined {
  if (!value) {
    return undefined;
  }
  if (Array.isArray(value)) {
    return value;
  }
  return lang === "sk" ? value.sk : value.en;
}
