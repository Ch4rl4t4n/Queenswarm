"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";
import type { DashboardOperatorMe, DeliveryChannelsPrefs } from "@/lib/hive-dashboard-session";

type ChannelKey = "email" | "sms" | "discord" | "telegram";

const CHANNEL_META: { key: ChannelKey; title: string; blurb: string }[] = [
  {
    key: "email",
    title: "E-mail",
    blurb: "Notifikácie na adresu ktorú nastavíš (worker musí mať SMTP v prostredí).",
  },
  {
    key: "sms",
    title: "SMS",
    blurb: "Telefón v tvare +421… (odosielanie závisí od Twilio / SMS provider v stacku).",
  },
  {
    key: "discord",
    title: "Discord",
    blurb: "Incoming webhook zo serverového Discord kanála.",
  },
  {
    key: "telegram",
    title: "Telegram",
    blurb: "Bot token + chat ID (uložené v tvojich preferenciách pre ďalšie odosielanie).",
  },
];

function readChannel(prefs: Record<string, unknown> | undefined, key: ChannelKey): Record<string, unknown> {
  const dc = prefs?.delivery_channels;
  if (!dc || typeof dc !== "object" || Array.isArray(dc)) {
    return {};
  }
  const ch = (dc as Record<string, unknown>)[key];
  if (!ch || typeof ch !== "object" || Array.isArray(ch)) {
    return {};
  }
  return ch as Record<string, unknown>;
}

export function SettingsNotificationsPanel() {
  const [me, setMe] = useState<DashboardOperatorMe | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<ChannelKey | null>("email");

  const [emailEn, setEmailEn] = useState(false);
  const [emailAddr, setEmailAddr] = useState("");
  const [smsEn, setSmsEn] = useState(false);
  const [smsPhone, setSmsPhone] = useState("");
  const [discordEn, setDiscordEn] = useState(false);
  const [discordUrl, setDiscordUrl] = useState("");
  const [tgEn, setTgEn] = useState(false);
  const [tgToken, setTgToken] = useState("");
  const [tgChat, setTgChat] = useState("");

  const load = useCallback(async () => {
    try {
      const m = await hiveGet<DashboardOperatorMe>("auth/me");
      setMe(m);
      setErr(null);
      const np = m.notification_prefs as DeliveryChannelsPrefs | Record<string, unknown>;
      const e = readChannel(np, "email");
      const s = readChannel(np, "sms");
      const d = readChannel(np, "discord");
      const t = readChannel(np, "telegram");
      setEmailEn(Boolean(e.enabled));
      setEmailAddr(typeof e.address === "string" ? e.address : "");
      setSmsEn(Boolean(s.enabled));
      setSmsPhone(typeof s.phone_e164 === "string" ? s.phone_e164 : "");
      setDiscordEn(Boolean(d.enabled));
      setDiscordUrl(typeof d.webhook_url === "string" ? d.webhook_url : "");
      setTgEn(Boolean(t.enabled));
      setTgToken(typeof t.bot_token === "string" ? t.bot_token : "");
      setTgChat(typeof t.chat_id === "string" ? t.chat_id : "");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Načítanie zlyhalo";
      setErr(msg);
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const summaryByChannel = useMemo(() => {
    if (!me) {
      return {} as Record<ChannelKey, string>;
    }
    const np = me.notification_prefs as Record<string, unknown>;
    return {
      email: readChannel(np, "email").enabled ? "zapnuté" : "vypnuté",
      sms: readChannel(np, "sms").enabled ? "zapnuté" : "vypnuté",
      discord: readChannel(np, "discord").enabled ? "zapnuté" : "vypnuté",
      telegram: readChannel(np, "telegram").enabled ? "zapnuté" : "vypnuté",
    } as Record<ChannelKey, string>;
  }, [me]);

  async function saveChannel(key: ChannelKey): Promise<void> {
    let payload: Record<string, Record<string, unknown>> = {};
    if (key === "email") {
      payload = { email: { enabled: emailEn, address: emailAddr.trim() || null } };
    } else if (key === "sms") {
      payload = { sms: { enabled: smsEn, phone_e164: smsPhone.trim() || null } };
    } else if (key === "discord") {
      payload = { discord: { enabled: discordEn, webhook_url: discordUrl.trim() || null } };
    } else {
      payload = {
        telegram: {
          enabled: tgEn,
          bot_token: tgToken.trim() || null,
          chat_id: tgChat.trim() || null,
        },
      };
    }

    setBusy(true);
    try {
      await hivePatchJson<DashboardOperatorMe>("auth/me/notifications", {
        delivery_channels: payload,
      });
      await load();
      toast.success("Preferencie kanála uložené.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Uloženie zlyhalo";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  if (err && !me) {
    return (
      <div className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6 text-sm text-danger">
        Notifikácie: {err}
      </div>
    );
  }

  if (!me) {
    return <div className="h-64 animate-pulse rounded-3xl bg-white/[0.04]" />;
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
          Notifikácie
        </h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Vyber kanály a rozklikni riadok, aby si doplnil prepojenie. Backend ukladá konfiguráciu do{' '}
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-400">
            notification_prefs.delivery_channels
          </span>
          — worker a integrácie ju môžu čítať pri odosielaní správ.
        </p>

        <ul className="mt-6 divide-y divide-white/[0.06] border-t border-white/[0.06]">
          {CHANNEL_META.map(({ key, title, blurb }) => {
            const expanded = open === key;
            return (
              <li key={key} className="py-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setOpen((o) => (o === key ? null : key))}
                  className="flex w-full items-center justify-between gap-3 rounded-xl px-2 py-3 text-left transition hover:bg-white/[0.03]"
                >
                  <div className="min-w-0">
                    <span className="font-[family-name:var(--font-inter)] text-sm font-semibold text-[#fafafa]">
                      {title}
                    </span>
                    <span className="ml-2 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                      · aktuálne {summaryByChannel[key]}
                    </span>
                    <p className="mt-0.5 font-[family-name:var(--font-inter)] text-xs text-zinc-600">{blurb}</p>
                  </div>
                  {expanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-pollen" aria-hidden />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-zinc-500" aria-hidden />
                  )}
                </button>

                {expanded ? (
                  <div className="rounded-xl border border-white/[0.07] bg-black/35 p-4">
                    {key === "email" ? (
                      <div className="space-y-3">
                        <label className="flex items-center gap-2 font-[family-name:var(--font-inter)] text-sm text-zinc-300">
                          <input
                            type="checkbox"
                            checked={emailEn}
                            onChange={(e) => setEmailEn(e.target.checked)}
                            className="rounded border-white/20"
                          />
                          Posielať e-mailové výstrahy
                        </label>
                        <label className="block font-[family-name:var(--font-inter)] text-xs uppercase text-zinc-500">
                          E-mail
                          <input
                            type="email"
                            value={emailAddr}
                            onChange={(e) => setEmailAddr(e.target.value)}
                            placeholder="bee@firma.sk"
                            className="mt-1 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/40"
                          />
                        </label>
                      </div>
                    ) : null}
                    {key === "sms" ? (
                      <div className="space-y-3">
                        <label className="flex items-center gap-2 font-[family-name:var(--font-inter)] text-sm text-zinc-300">
                          <input
                            type="checkbox"
                            checked={smsEn}
                            onChange={(e) => setSmsEn(e.target.checked)}
                            className="rounded border-white/20"
                          />
                          SMS výstrahy
                        </label>
                        <label className="block font-[family-name:var(--font-inter)] text-xs uppercase text-zinc-500">
                          Telefón (E.164)
                          <input
                            type="tel"
                            value={smsPhone}
                            onChange={(e) => setSmsPhone(e.target.value)}
                            placeholder="+421912345678"
                            className="mt-1 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa] outline-none focus:border-pollen/40"
                          />
                        </label>
                      </div>
                    ) : null}
                    {key === "discord" ? (
                      <div className="space-y-3">
                        <label className="flex items-center gap-2 font-[family-name:var(--font-inter)] text-sm text-zinc-300">
                          <input
                            type="checkbox"
                            checked={discordEn}
                            onChange={(e) => setDiscordEn(e.target.checked)}
                            className="rounded border-white/20"
                          />
                          Discord webhook
                        </label>
                        <label className="block font-[family-name:var(--font-inter)] text-xs uppercase text-zinc-500">
                          Webhook URL
                          <input
                            type="url"
                            value={discordUrl}
                            onChange={(e) => setDiscordUrl(e.target.value)}
                            placeholder="https://discord.com/api/webhooks/…"
                            className="mt-1 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[#fafafa] outline-none focus:border-pollen/40"
                          />
                        </label>
                      </div>
                    ) : null}
                    {key === "telegram" ? (
                      <div className="space-y-3">
                        <label className="flex items-center gap-2 font-[family-name:var(--font-inter)] text-sm text-zinc-300">
                          <input
                            type="checkbox"
                            checked={tgEn}
                            onChange={(e) => setTgEn(e.target.checked)}
                            className="rounded border-white/20"
                          />
                          Telegram Bot
                        </label>
                        <label className="block font-[family-name:var(--font-inter)] text-xs uppercase text-zinc-500">
                          Bot token
                          <input
                            type="password"
                            value={tgToken}
                            onChange={(e) => setTgToken(e.target.value)}
                            autoComplete="off"
                            placeholder="token od @BotFather"
                            className="mt-1 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-[#fafafa] outline-none focus:border-pollen/40"
                          />
                        </label>
                        <label className="block font-[family-name:var(--font-inter)] text-xs uppercase text-zinc-500">
                          Chat ID
                          <input
                            type="text"
                            value={tgChat}
                            onChange={(e) => setTgChat(e.target.value)}
                            placeholder="numerický alebo @channel_username"
                            className="mt-1 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa] outline-none focus:border-pollen/40"
                          />
                        </label>
                      </div>
                    ) : null}

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void saveChannel(key)}
                      className="mt-4 rounded-full border border-pollen bg-pollen px-5 py-2 font-[family-name:var(--font-inter)] text-xs font-bold text-black shadow-[0_0_18px_rgb(255_184_0/0.25)] disabled:opacity-40"
                    >
                      Uložiť {title}
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
