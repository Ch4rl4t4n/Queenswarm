"use client";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { HIVE_MAIN_CONTENT_ID } from "@/lib/hive-a11y";
import { localizePhrase } from "@/lib/ui-copy";

/** First Tab stop — jumps keyboard users to primary canvas content. */
export function SkipToMainLink(): JSX.Element {
  const { language } = useUiLanguage();

  return (
    <a href={`#${HIVE_MAIN_CONTENT_ID}`} className="hive-skip-link">
      {localizePhrase(language, { en: "Skip to main content", sk: "Preskočiť na hlavný obsah" })}
    </a>
  );
}
