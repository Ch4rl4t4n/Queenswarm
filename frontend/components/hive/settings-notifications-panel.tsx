"use client";

import { ChevronDown, Mail, MessageSquare, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import { Toggle } from "@/components/ui/toggle";
import { V4Badge, V4Card } from "@/components/ui/v4";
import { V4FormField, V4FormStack } from "@/components/ui/v4/v4-form-field";
import type { NotificationChannelListRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type ChannelSlug = "email" | "sms" | "discord" | "teams" | "telegram";

const CHANNEL_SLUGS: ChannelSlug[] = ["email", "sms", "discord", "teams", "telegram"];

const EVENTS: Record<ChannelSlug, string> = {
  email: "task_complete · agent_error_digest · weekly_summary",
  sms: "severity_p0_only",
  discord: "waggle_hints · Ballroom transcripts",
  teams: "supervisor_digest · operator alerts",
  telegram: "task_complete · ballroom_ping",
};

const META: Record<ChannelSlug, { title: string; Icon: typeof Mail }> = {
  email: { title: "Email", Icon: Mail },
  sms: { title: "SMS", Icon: Send },
  discord: { title: "Discord", Icon: MessageSquare },
  teams: { title: "Microsoft Teams", Icon: MessageSquare },
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
    case "teams":
      return { webhook_url: "", enabled: false };
    case "telegram":
      return { bot_token: "", chat_id: "", enabled: false };
    default:
      return {};
  }
}

function isProxyUnreachableMessage(msg: string): boolean {
  return msg.toLowerCase().includes("proxy_upstream_unreachable");
}

function hintProxyFailure(msg: string): string {
  if (!isProxyUnreachableMessage(msg)) {
    return msg;
  }
  return `${msg} Ensure the API is running and Next has INTERNAL_BACKEND_ORIGIN (e.g. http://127.0.0.1:8000 for local dev).`;
}

export function SettingsNotificationsPanel() {
  const [channels, setChannels] = useState<NotificationChannelListRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [openSlug, setOpenSlug] = useState<ChannelSlug | null>("email");
  const [drafts, setDrafts] = useState<
    Record<ChannelSlug, { enabled: boolean; settings: Record<string, unknown>; label?: string }>
  >({
    email: { enabled: true, settings: channelDraftDefaults("email") },
    sms: { enabled: false, settings: channelDraftDefaults("sms") },
    discord: { enabled: false, settings: channelDraftDefaults("discord") },
    teams: { enabled: false, settings: channelDraftDefaults("teams") },
    telegram: { enabled: false, settings: channelDraftDefaults("telegram") },
  });
  const [testHints, setTestHints] = useState<Partial<Record<ChannelSlug, string>>>({});

  const hydrateDraftsFromApi = useCallback((rows: NotificationChannelListRow[]) => {
    setDrafts((prev) => {
      const next = { ...prev };
      for (const slug of CHANNEL_SLUGS) {
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
                  : slug === "teams"
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
    if (slug === "teams" && blob.enabled && !String(blob.settings.webhook_url ?? "").trim()) {
      toast.error("Teams webhook required when enabled.");
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
      toast.error(hintProxyFailure(msg));
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
      toast.error(hintProxyFailure(msg));
    } finally {
      setBusy(false);
    }
  }

  async function sendTest(slug: ChannelSlug): Promise<void> {
    const savedRow = channels.find((c) => c.channel_type === slug || c.id === slug);
    if (!savedRow) {
      const hint = "Save the channel first so the hive can store webhook or address settings.";
      toast.error(hint);
      setTestHints((h) => ({ ...h, [slug]: `❌ ${hint}` }));
      return;
    }

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
        const shown = hintProxyFailure(msg);
        setTestHints((h) => ({ ...h, [slug]: `❌ ${shown}` }));
        toast.error(shown);
      }
    } finally {
      setBusy(false);
    }
  }

  if (err && channels.length === 0) {
    return (
      <V4Card className="border-danger/30 bg-danger/6 text-danger">
        Notifications: {err}
      </V4Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-(--qs-text-3)">
        Delivery buckets sync to{" "}
        <span className="font-mono text-xs text-pollen">notification_prefs.delivery_channels</span> via{" "}
        <span className="font-mono text-xs text-pollen">/api/v1/notifications</span>.
      </p>

      <div className="flex flex-col gap-2">
        {CHANNEL_SLUGS.map((slug) => {
          const { Icon, title } = META[slug];
          const blob = drafts[slug];
          const row = channels.find((c) => c.channel_type === slug || c.id === slug);
          const configured = row?.is_active;
          const open = openSlug === slug;
          const panelId = `notif-channel-${slug}`;

          return (
            <V4Card key={slug} tight className={cn("overflow-hidden p-0", open && "v4-settings-notify-tab--open")}>
              <button
                type="button"
                className="v4-settings-notify-tab"
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpenSlug((current) => (current === slug ? null : slug))}
              >
                <span className="v4-settings-notify-tab-icon" aria-hidden>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1 text-left">
                  <h3 className="truncate text-sm font-semibold text-(--qs-text)">{title}</h3>
                  <p className="mt-0.5 truncate text-xs text-(--qs-text-3)">{EVENTS[slug]}</p>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  {configured ? (
                    <V4Badge tone="ok" className="shrink-0 whitespace-nowrap">
                      configured
                    </V4Badge>
                  ) : null}
                  <V4Badge tone={blob.enabled ? "ok" : "info"} className="tabular-nums">
                    {blob.enabled ? "On" : "Off"}
                  </V4Badge>
                  <span className={cn("v4-panel-collapsible-chevron", open && "v4-panel-collapsible-chevron--open")} aria-hidden>
                    <ChevronDown className="h-4 w-4" />
                  </span>
                </span>
              </button>

              {open ? (
                <div id={panelId} className="v4-settings-notify-tab-body">
                  <div className="mb-3 flex items-center justify-between gap-3 text-[13px] text-(--qs-text)">
                    <span>Enabled</span>
                    <Toggle
                      checked={blob.enabled}
                      disabled={busy}
                      onChange={(next) =>
                        setDrafts((d) => ({
                          ...d,
                          [slug]: { ...d[slug], enabled: next },
                        }))
                      }
                      aria-label={`${title} channel enabled`}
                    />
                  </div>

                  <V4FormStack>
                    {slug === "email" ? (
                      <V4FormField label="Address" htmlFor={`notif-email-${slug}`}>
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
                      </V4FormField>
                    ) : null}

                    {slug === "sms" ? (
                      <V4FormField label="Phone (E.164)" htmlFor={`notif-sms-${slug}`}>
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
                      </V4FormField>
                    ) : null}

                    {slug === "discord" || slug === "teams" ? (
                      <V4FormField label="Webhook URL" htmlFor={`notif-${slug}-${slug}`}>
                        <input
                          id={`notif-${slug}-${slug}`}
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
                          placeholder={slug === "teams" ? "https://outlook.office.com/webhook/…" : undefined}
                        />
                      </V4FormField>
                    ) : null}

                    {slug === "telegram" ? (
                      <div className="v4-settings-notify-fields grid gap-3 sm:grid-cols-2">
                        <V4FormField label="Bot token" htmlFor={`tg-token-${slug}`}>
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
                        </V4FormField>
                        <V4FormField label="Chat ID" htmlFor={`tg-chat-${slug}`}>
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
                        </V4FormField>
                      </div>
                    ) : null}
                  </V4FormStack>

                  <div className="v4-settings-notify-actions mt-4 flex flex-wrap gap-2">
                    <button type="button" disabled={busy} onClick={() => void saveChannel(slug)} className="qs-btn qs-btn--primary qs-btn--sm">
                      Save channel
                    </button>
                    <button type="button" disabled={busy} onClick={() => void sendTest(slug)} className="qs-btn qs-btn--cyan qs-btn--sm">
                      Send test
                    </button>
                    <button type="button" disabled={busy} onClick={() => void clearChannel(slug)} className="qs-btn qs-btn--danger qs-btn--sm">
                      Clear
                    </button>
                  </div>

                  {testHints[slug] ? (
                    <p
                      className={cn(
                        "mt-3 font-mono text-[11px]",
                        testHints[slug]?.startsWith("✅") ? "text-(--qs-green)" : "text-(--qs-red)",
                      )}
                    >
                      {testHints[slug]}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </V4Card>
          );
        })}
      </div>
    </div>
  );
}
