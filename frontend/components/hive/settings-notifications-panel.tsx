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
          settings:
            slug === "email"
              ? { address: "" }
              : slug === "sms"
                ? { phone_e164: "" }
                : slug === "discord"
                  ? { webhook_url: "" }
                  : { bot_token: "", chat_id: "" },
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
    if (slug === "email" && blob.enabled && !String(blob.settings.address ?? "").trim()) {
      toast.error("Email address required when channel is enabled.");
      return;
    }
    if (slug === "sms" && blob.enabled && !String(blob.settings.phone_e164 ?? "").trim()) {
      toast.error("E.164 phone required for SMS.");
      return;
    }
    if (slug === "discord" && blob.enabled && !String(blob.settings.webhook_url ?? "").trim()) {
      toast.error("Discord webhook required when enabled.");
      return;
    }
    if (slug === "telegram" && blob.enabled) {
      if (!String(blob.settings.bot_token ?? "").trim() || !String(blob.settings.chat_id ?? "").trim()) {
        toast.error("Telegram bot token + chat id required when enabled.");
        return;
      }
    }
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
      <div className="qs-settings-card border-[var(--qs-red)]/30 bg-[var(--qs-red)]/[0.06] text-[var(--qs-red)]">
        Notifications: {err}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-[var(--qs-gap)]">
      <p className="font-[family-name:var(--font-inter)] text-sm text-[var(--qs-text-3)]">
        Delivery buckets sync to{" "}
        <span className="font-mono text-xs text-[var(--qs-cyan)]">notification_prefs.delivery_channels</span> via{" "}
        <span className="font-mono text-xs text-[var(--qs-cyan)]">/api/v1/notifications</span>.
      </p>

      <div className="flex flex-col gap-0">
        {(["email", "sms", "discord", "telegram"] as ChannelSlug[]).map((slug) => {
          const { Icon, title } = META[slug];
          const blob = drafts[slug];
          const row = channels.find((c) => c.channel_type === slug || c.id === slug);
          const configured = row?.is_active;

          return (
            <article key={slug} className="qs-settings-card">
              <header className="qs-settings-card__header !mb-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[var(--qs-border)] bg-[var(--qs-bg)] text-[var(--qs-amber)]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <div className="qs-settings-card__title">{title}</div>
                    <div className="qs-settings-card__subtitle">{EVENTS[slug]}</div>
                  </div>
                </div>
              </header>

              {configured ? <span className="qs-badge qs-badge--green mb-3">configured</span> : null}

              <label className="mb-3 flex cursor-pointer items-center gap-2 text-[13px] text-[var(--qs-text)]">
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 rounded border-[var(--qs-border)] accent-[var(--qs-amber)]"
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
                <div className="mb-3">
                  <label className="qs-label" htmlFor={`notif-email-${slug}`}>
                    Address
                  </label>
                  <input
                    id={`notif-email-${slug}`}
                    type="email"
                    disabled={busy}
                    value={String(blob.settings.address ?? "")}
                    onChange={(e) =>
                      setDrafts((d) => ({
                        ...d,
                        [slug]: { ...d[slug], settings: { ...d[slug].settings, address: e.target.value } },
                      }))
                    }
                    className="qs-input"
                  />
                </div>
              ) : null}

              {slug === "sms" ? (
                <div className="mb-3">
                  <label className="qs-label" htmlFor={`notif-sms-${slug}`}>
                    Phone (E.164)
                  </label>
                  <input
                    id={`notif-sms-${slug}`}
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
                    className="qs-input"
                  />
                </div>
              ) : null}

              {slug === "discord" ? (
                <div className="mb-3">
                  <label className="qs-label" htmlFor={`notif-discord-${slug}`}>
                    Webhook URL
                  </label>
                  <input
                    id={`notif-discord-${slug}`}
                    type="password"
                    disabled={busy}
                    value={String(blob.settings.webhook_url ?? "")}
                    onChange={(e) =>
                      setDrafts((d) => ({
                        ...d,
                        [slug]: { ...d[slug], settings: { ...d[slug].settings, webhook_url: e.target.value } },
                      }))
                    }
                    className="qs-input"
                  />
                </div>
              ) : null}

              {slug === "telegram" ? (
                <div className="mb-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="qs-label" htmlFor={`tg-token-${slug}`}>
                      Bot token
                    </label>
                    <input
                      id={`tg-token-${slug}`}
                      type="password"
                      disabled={busy}
                      value={String(blob.settings.bot_token ?? "")}
                      onChange={(e) =>
                        setDrafts((d) => ({
                          ...d,
                          [slug]: { ...d[slug], settings: { ...d[slug].settings, bot_token: e.target.value } },
                        }))
                      }
                      className="qs-input"
                    />
                  </div>
                  <div>
                    <label className="qs-label" htmlFor={`tg-chat-${slug}`}>
                      Chat ID
                    </label>
                    <input
                      id={`tg-chat-${slug}`}
                      type="text"
                      disabled={busy}
                      value={String(blob.settings.chat_id ?? "")}
                      onChange={(e) =>
                        setDrafts((d) => ({
                          ...d,
                          [slug]: { ...d[slug], settings: { ...d[slug].settings, chat_id: e.target.value } },
                        }))
                      }
                      className="qs-input"
                    />
                  </div>
                </div>
              ) : null}

              <div className="mt-1 flex flex-wrap gap-2">
                <button type="button" disabled={busy} onClick={() => void saveChannel(slug)} className="qs-btn qs-btn--primary qs-btn--sm">
                  Save channel
                </button>
                <button type="button" disabled={busy} onClick={() => void sendTest(slug)} className="qs-btn qs-btn--test qs-btn--sm">
                  Send test
                </button>
                <button type="button" disabled={busy} onClick={() => void clearChannel(slug)} className="qs-btn qs-btn--danger qs-btn--sm">
                  Clear
                </button>
              </div>

              {testHints[slug] ? (
                <p
                  className={cn(
                    "font-mono text-[11px]",
                    testHints[slug]?.startsWith("✅") ? "text-[var(--qs-green)]" : "text-[var(--qs-red)]",
                  )}
                >
                  {testHints[slug]}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}
