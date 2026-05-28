"use client";

import { Download, Share, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { MEDIA_QUERIES } from "@/lib/breakpoints";
import { useModalA11y } from "@/lib/use-modal-a11y";
import {
  bumpVisitCount,
  dismissInstallPrompt,
  isInstallDismissed,
  isIosSafari,
  isStandalonePwa,
  shouldOfferInstallPrompt,
} from "@/lib/pwa-install";
import { localizePhrase } from "@/lib/ui-copy";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** Bottom install sheet — mobile/tablet only, after 2nd session visit. */
export function HiveInstallPrompt(): JSX.Element | null {
  const pathname = usePathname();
  const { language } = useUiLanguage();
  const [visible, setVisible] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [iosHint, setIosHint] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const onDismiss = (): void => {
    dismissInstallPrompt(localStorage);
    setVisible(false);
  };

  useModalA11y({
    open: visible,
    onClose: onDismiss,
    containerRef: panelRef,
    lockScroll: false,
  });

  const evaluate = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }

    const belowDesktop = window.matchMedia(MEDIA_QUERIES.belowDesktop).matches;
    const visits = bumpVisitCount(sessionStorage, localStorage);
    const offer = shouldOfferInstallPrompt({
      belowDesktop,
      standalone: isStandalonePwa(),
      dismissed: isInstallDismissed(localStorage),
      visits,
      pathname,
    });

    setIosHint(isIosSafari());
    setVisible(offer);
  }, [pathname]);

  useEffect(() => {
    evaluate();

    const mq = window.matchMedia(MEDIA_QUERIES.belowDesktop);
    const onMq = (): void => evaluate();
    mq.addEventListener("change", onMq);

    const onBip = (event: Event): void => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", onBip);
    return () => {
      mq.removeEventListener("change", onMq);
      window.removeEventListener("beforeinstallprompt", onBip);
    };
  }, [evaluate]);

  const onInstall = async (): Promise<void> => {
    if (!deferredPrompt) {
      onDismiss();
      return;
    }
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    setVisible(false);
  };

  if (!visible) {
    return null;
  }

  const canNativeInstall = deferredPrompt !== null;

  return (
    <div
      ref={panelRef}
      data-hive-install-prompt
      role="dialog"
      aria-modal="false"
      aria-labelledby="hive-install-title"
      className="hive-install-prompt fixed inset-x-3 z-[190] mx-auto max-w-lg rounded-2xl border border-pollen/35 bg-[#0a0a12]/95 p-4 shadow-[0_0_32px_rgb(255_184_0/0.18)] backdrop-blur-lg lg:hidden"
      style={{
        bottom: "calc(var(--qs-shell-bottom-nav-h) + 0.75rem + env(safe-area-inset-bottom, 0px))",
      }}
    >
      <div className="flex items-start gap-3">
        <span className="hive-hex mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center border-[4px] border-black/55 bg-gradient-to-br from-pollen to-amber-600 shadow-[0_0_18px_rgb(255_184_0/0.45)]">
          <Download className="h-4 w-4 text-black" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p
            id="hive-install-title"
            className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen"
          >
            {localizePhrase(language, {
              en: "Install Queenswarm Hive",
              sk: "Nainštaluj Queenswarm Hive",
            })}
          </p>
          <p className="mt-1 font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-zinc-400">
            {iosHint
              ? localizePhrase(language, {
                  en: "Tap Share, then “Add to Home Screen” for offline shell + faster launch.",
                  sk: "Klepnite Zdieľať → „Pridať na plochu“ pre offline shell a rýchlejší štart.",
                })
              : localizePhrase(language, {
                  en: "Add to home screen for offline shell and one-tap hive access.",
                  sk: "Pridajte na plochu pre offline shell a rýchly prístup k hive.",
                })}
          </p>
          {iosHint ? (
            <p className="mt-2 flex items-center gap-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-wider text-cyan/80">
              <Share className="h-3 w-3" aria-hidden />
              {localizePhrase(language, { en: "Share → Add to Home Screen", sk: "Zdieľať → Pridať na plochu" })}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[color:var(--qs-border)] text-zinc-400 hover:text-pollen touch-manipulation"
          aria-label={localizePhrase(language, { en: "Dismiss", sk: "Zavrieť" })}
          onClick={onDismiss}
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
      <div className="mt-3 flex gap-2">
        {!iosHint && canNativeInstall ? (
          <button
            type="button"
            className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl bg-pollen px-4 font-[family-name:var(--font-poppins)] text-sm font-semibold text-black touch-manipulation"
            onClick={() => void onInstall()}
          >
            {localizePhrase(language, { en: "Install app", sk: "Nainštalovať" })}
          </button>
        ) : null}
        <button
          type="button"
          className="inline-flex min-h-11 flex-1 items-center justify-center rounded-xl border border-[color:var(--qs-border)] bg-black/40 px-4 font-[family-name:var(--font-poppins)] text-sm text-zinc-300 touch-manipulation"
          onClick={onDismiss}
        >
          {localizePhrase(language, { en: "Not now", sk: "Teraz nie" })}
        </button>
      </div>
    </div>
  );
}
