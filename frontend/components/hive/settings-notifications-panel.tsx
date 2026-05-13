"use client";

import { Mail, MessageSquare, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { NotificationChannelListRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type ChannelSlug = "email" | "sms" | "discord" | "telegram";

const EVENTS: Record<ChannelSlug, string> = {
  email: "task_complete · agent_error_digest · weekly_summary",
  sms: "severity_p0_only",
  discord: "waggle_hints · Ballroom transcripts",
  telegram: "task_complete · ballroom_ping",
};

const META: Record<ChannelSlug, { title: string; Icon: typeof Mail }> = {
  email: { title: "Email", Icon: Mail },
  sms: { title: "SMS", Icon: Send },
  discord: { title: "Discord", Icon: MessageSquare },
  telegram: { title: "Telegram", Icon: Send },
};

function channelDraftDefaults(slug: ChannelSlug): Record<string, unknown> {
  switch (slug) {
    case "email":
      return { address: "", enabled: true };
    case "sms":
      return { phone_e164: "", enabled: false };
    case "discord":
      return { webhook_url: "", enabled: false };
    case "telegram":
      return { bot_token: "", chat_id: "", enabled: false };
    default:
      return {};
  }
}

export function SettingsNotificationsPanel() {
  const [channels, setChannels] = useState<NotificationChannelListRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<
    Record<ChannelSlug, { enabled: boolean; settings: Record<string, unknown>; label?: string }>
  >({
    email: { enabled: true, settings: channelDraftDefaults("email") },
    sms: { enabled: false, settings: channelDraftDefaults("sms") },
    discord: { enabled: false, settings: channelDraftDefaults("discord") },
    telegram: { enabled: false, settings: channelDraftDefaults("telegram") },
  });
  const [testHints, setTestHints] = useState<Partial<Record<ChannelSlug, string>>>({});

  const hydrateDraftsFromApi = useCallback((rows: NotificationChannelListRow[]) => {
    setDrafts((prev) => {
      const next = { ...prev };
      for (const slug of ["email", "sms", "discord", "telegram"] as ChannelSlug[]) {
        const row = rows.find((r) => r.channel_type === slug || r.id === slug);
        if (!row) {
          continue;
        }
        /** Masked payloads are display-only — editing requires pasting fresh secrets. */
        next[slug] = {
          enabled: row.is_active,
          label: row.label,
          settings: slug === "email" ? { address: "" } : slug === "sms" ? { phone_e164: "" } : slug === "discord" ? { webhook_url: "" } : { bot_token: "", chat_id: "" },
        };
      }
      return next;
    });
  }, []);

  const load = useCallback(async () => {
    try {
      const bundle = await hiveGet<{ channels: NotificationChannelListRow[] }>("notifications");
      const list = bundle.channels ?? [];
      setChannels(list);
      hydrateDraftsFromApi(list);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Load failed";
      setErr(msg);
      setChannels([]);
    }
  }, [hydrateDraftsFromApi]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveChannel(slug: ChannelSlug): Promise<void> {
    const blob = drafts[slug];
    setBusy(true);
    try {
      await hivePostJson("notifications/", {
        channel_type: slug,
        enabled: blob.enabled,
        label: blob.label ?? META[slug].title,
        settings: blob.settings,
      });
      setTestHints((h) => ({ ...h, [slug]: undefined }));
      toast.success(`${META[slug].title} merged`);
      const bundle = await hiveGet<{ channels: NotificationChannelListRow[] }>("notifications");
      const list = bundle.channels ?? [];
      setChannels(list);
      hydrateDraftsFromApi(list);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Save failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function clearChannel(slug: ChannelSlug): Promise<void> {
    if (!window.confirm(`Disconnect ${META[slug].title}?`)) {
      return;
    }
    setBusy(true);
    try {
      await hiveDelete(`notifications/${slug}`);
      toast.success("Channel cleared");
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Delete failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function sendTest(slug: ChannelSlug): Promise<void> {
    setBusy(true);
    try {
      const res = await hivePostJson<{ status?: string; detail?: string }>(`notifications/test/${slug}`, {});
      const ok = res.status === "ok";
      setTestHints((h) => ({
        ...h,
        [slug]: ok ? "✅ Delivery accepted" : `❌ ${res.detail ?? "Failed"}`,
      }));
      if (!ok) {
        toast.error(res.detail ?? "Test failed");
      }
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Test failed";
      if (e instanceof HiveApiError && e.status === 501 && slug === "email") {
        setTestHints((h) => ({ ...h, email: "ℹ️ Email smoke uses global SMTP + /system notify-test." }));
        toast.message("Email test not wired for channel ping");
      } else {
        setTestHints((h) => ({ ...h, [slug]: `❌ ${msg}` }));
        toast.error(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  if (err && channels.length === 0) {
    return (
      <div className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6 text-sm text-danger">
        Notifications: {err}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="font-[family-name:var(--font-inter)] text-sm text-zinc-500">
        Delivery buckets sync to <span className="font-mono text-xs text-data">notification_prefs.delivery_channels</span> via{" "}
        <span className="font-mono text-xs text-data">/api/v1/notifications</span>.
      </p>

      <div className="grid gap-5">
        {(["email", "sms", "discord", "telegram"] as ChannelSlug[]).map((slug) => {
          const { Icon, title } = META[slug];
          const blob = drafts[slug];
          return (
            <section key={slug} className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan/20 bg-black/40 text-pollen">
                    <Icon className="h-5 w-5" aria-hidden />
                  </div>
                  <div>
                    <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">{title}</h2>
                    <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-500">{EVENTS[slug]}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void sendTest(slug)}
                    className="rounded-full border border-data/35 px-4 py-2 text-xs font-semibold text-data hover:bg-data/10 disabled:opacity-40"
                  >
                    Send test
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void clearChannel(slug)}
                    className="rounded-full border border-danger/35 px-4 py-2 text-xs font-semibold text-danger hover:bg-danger/10 disabled:opacity-40"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <label className="mt-4 flex items-center gap-2 font-[family-name:var(--font-inter)] text-sm text-zinc-300">
                <input
                  type="checkbox"
                  checked={blob.enabled}
                  disabled={busy}
                  onChange={(e) =>
                    setDrafts((d) => ({
                      ...d,
                      [slug]: { ...d[slug], enabled: e.target.checked },
                    }))
                  }
                />
                Enabled
              </label>

              {slug === "email" ? (
                <label className="mt-3 block text-xs uppercase tracking-[0.12em] text-zinc-500">
                  Address
                  <input
                    type="email"
                    disabled={busy}
                    value={String(blob.settings.address ?? "")}
                    onChange={(e) =>
                      setDrafts((d) => ({
                        ...d,
                        [slug]: { ...d[slug], settings: { ...d[slug].settings, address: e.target.value } },
                      }))
                    }
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 text-sm text-[#fafafa]"
                  />
                </label>
              ) : null}

              {slug === "sms" ? (
                <label className="mt-3 block text-xs uppercase tracking-[0.12em] text-zinc-500">
                  Phone (E.164)
                  <input
                    type="tel"
                    disabled={busy}
                    value={String(blob.settings.phone_e164 ?? "")}
                    onChange={(e) =>
                      setDrafts((d) => ({
                        ...d,
                        [slug]: { ...d[slug], settings: { ...d[slug].settings, phone_e164: e.target.value } },
                      }))
                    }
                    placeholder="+4219…"
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 text-sm text-[#fafafa]"
                  />
                </label>
              ) : null}

              {slug === "discord" ? (
                <label className="mt-3 block text-xs uppercase tracking-[0.12em] text-zinc-500">
                  Webhook URL
                  <input
                    type="password"
                    disabled={busy}
                    value={String(blob.settings.webhook_url ?? "")}
                    onChange={(e) =>
                      setDrafts((d) => ({
                        ...d,
                        [slug]: { ...d[slug], settings: { ...d[slug].settings, webhook_url: e.target.value } },
                      }))
                    }
                    className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-mono text-sm text-[#fafafa]"
                  />
                </label>
              ) : null}

              {slug === "telegram" ? (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="block text-xs uppercase tracking-[0.12em] text-zinc-500">
                    Bot token
                    <input
                      type="password"
                      disabled={busy}
                      value={String(blob.settings.bot_token ?? "")}
                      onChange={(e) =>
                        setDrafts((d) => ({
                          ...d,
                          [slug]: { ...d[slug], settings: { ...d[slug].settings, bot_token: e.target.value } },
                        }))
                      }
                      className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-mono text-sm text-[#fafafa]"
                    />
                  </label>
                  <label className="block text-xs uppercase tracking-[0.12em] text-zinc-500">
                    Chat ID
                    <input
                      type="text"
                      disabled={busy}
                      value={String(blob.settings.chat_id ?? "")}
                      onChange={(e) =>
                        setDrafts((d) => ({
                          ...d,
                          [slug]: { ...d[slug], settings: { ...d[slug].settings, chat_id: e.target.value } },
                        }))
                      }
                      className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-mono text-sm text-[#fafafa]"
                    />
                  </label>
                </div>
              ) : null}

              <button
                type="button"
                disabled={busy}
                onClick={() => void saveChannel(slug)}
                className="mt-4 rounded-full border border-pollen bg-pollen px-5 py-2.5 text-xs font-bold text-black shadow-[0_0_18px_rgb(255_184_0/0.25)] hover:bg-[#ffc933] disabled:opacity-40"
              >
                Save channel
              </button>
              {testHints[slug] ? (
                <p className={cn("mt-3 font-[family-name:var(--font-jetbrains-mono)] text-xs", testHints[slug]?.startsWith("✅") ? "text-success" : "text-danger")}>
                  {testHints[slug]}
                </p>
              ) : null}
            </section>
          );
        })}
      </div>
    </div>
  );
}
