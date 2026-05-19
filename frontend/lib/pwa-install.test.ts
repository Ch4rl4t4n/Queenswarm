import { describe, expect, it } from "vitest";

import {
  PWA_DISMISS_MS,
  bumpVisitCount,
  dismissInstallPrompt,
  isInstallDismissed,
  isIosSafari,
  isStandalonePwa,
  readVisitCount,
  shouldOfferInstallPrompt,
} from "./pwa-install";

describe("pwa-install", () => {
  it("shouldOfferInstallPrompt_when_second_visit_on_mobile", () => {
    expect(
      shouldOfferInstallPrompt({
        belowDesktop: true,
        standalone: false,
        dismissed: false,
        visits: 2,
        pathname: "/swarms",
      }),
    ).toBe(true);
  });

  it("shouldOfferInstallPrompt_false_on_desktop", () => {
    expect(
      shouldOfferInstallPrompt({
        belowDesktop: false,
        standalone: false,
        dismissed: false,
        visits: 5,
        pathname: "/swarms",
      }),
    ).toBe(false);
  });

  it("shouldOfferInstallPrompt_false_on_login", () => {
    expect(
      shouldOfferInstallPrompt({
        belowDesktop: true,
        standalone: false,
        dismissed: false,
        visits: 3,
        pathname: "/login",
      }),
    ).toBe(false);
  });

  it("bumpVisitCount_increments_once_per_session", () => {
    const session = new Map<string, string>();
    const local = new Map<string, string>();
    const sessionStore = {
      getItem: (k: string) => session.get(k) ?? null,
      setItem: (k: string, v: string) => {
        session.set(k, v);
      },
    };
    const localStore = {
      getItem: (k: string) => local.get(k) ?? null,
      setItem: (k: string, v: string) => {
        local.set(k, v);
      },
    };

    expect(bumpVisitCount(sessionStore, localStore)).toBe(1);
    expect(bumpVisitCount(sessionStore, localStore)).toBe(1);
    expect(readVisitCount(localStore)).toBe(1);
  });

  it("isInstallDismissed_respects_expiry", () => {
    const store = new Map<string, string>();
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v);
      },
    };
    dismissInstallPrompt(storage, 1_000);
    expect(isInstallDismissed(storage, 1_000 + PWA_DISMISS_MS - 1)).toBe(true);
    expect(isInstallDismissed(storage, 1_000 + PWA_DISMISS_MS + 1)).toBe(false);
  });

  it("isIosSafari_detects_iphone_safari", () => {
    const ua =
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";
    expect(isIosSafari(ua, 5)).toBe(true);
  });

  it("isStandalonePwa_false_for_regular_chrome_android", () => {
    expect(isStandalonePwa()).toBe(false);
  });
});
