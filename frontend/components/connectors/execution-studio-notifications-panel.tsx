"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import {
  subscribeExecutionStudioWebPush,
  unsubscribeExecutionStudioWebPush,
} from "@/lib/execution-studio-web-push";
import { setExecutionStudioPushIntent } from "@/lib/execution-studio-push-session-sync";
import {
  clearWebhookTestStatusChannel,
  loadWebhookTestStatus,
  saveWebhookTestStatus,
} from "@/lib/execution-studio-webhook-test-status";
import { formatTestedAgo } from "@/lib/format-tested-ago";
import { SlackMarkdownPreview } from "@/lib/slack-markdown-preview";
import { cn } from "@/lib/utils";

type WebhookChannel = "slack" | "discord" | "teams" | "telegram";
type WebhookTestResult = "ok" | "fail";

type WebhookTestChannelKey = WebhookChannel | "email";
type WebhookTestStatusRow = { status: WebhookTestResult; tested_at?: string | null };

export interface StudioNotifications {
  email_recipients: string[];
  slack_webhook_url?: string;
  discord_webhook_url?: string;
  teams_webhook_url?: string;
  telegram_bot_token?: string;
  telegram_chat_id?: string;
  last_weekly_rollup_at?: string | null;
  weekly_rollup_enabled?: boolean;
  webhook_test_status?: Partial<Record<WebhookChannel | "email", WebhookTestStatusRow | WebhookTestResult>>;
  webhook_test_history?: Array<{ channel: string; status: WebhookTestResult; tested_at?: string }>;
  web_push_configured?: boolean;
  web_push_subscribed?: boolean;
}

interface ExecutionStudioNotificationsPanelProps {
  notifications: StudioNotifications | undefined;
  loading: boolean;
  onNotificationsChange: (notifications: StudioNotifications) => void;
  onError: (message: string | null) => void;
  onReloadOverview: () => Promise<void>;
}

function parseServerWebhookTestStatus(
  raw: Partial<Record<WebhookTestChannelKey, WebhookTestStatusRow | WebhookTestResult>> | undefined,
): {
  statuses: Partial<Record<WebhookTestChannelKey, WebhookTestResult>>;
  timestamps: Partial<Record<WebhookTestChannelKey, string>>;
} {
  const statuses: Partial<Record<WebhookTestChannelKey, WebhookTestResult>> = {};
  const timestamps: Partial<Record<WebhookTestChannelKey, string>> = {};
  for (const [key, value] of Object.entries(raw ?? {})) {
    const channel = key as WebhookTestChannelKey;
    if (typeof value === "string") {
      statuses[channel] = value;
      continue;
    }
    if (value && typeof value === "object" && "status" in value) {
      statuses[channel] = value.status;
      if (value.tested_at) {
        timestamps[channel] = value.tested_at;
      }
    }
  }
  return { statuses, timestamps };
}

function WebhookChannelStatusIcon({
  status,
  contextLabel = "Webhook",
}: {
  status: WebhookTestResult | null | undefined;
  contextLabel?: string;
}) {
  if (status === "ok") {
    return (
      <CheckCircle2
        className="h-3.5 w-3.5 text-verified"
        aria-label={`${contextLabel} test passed`}
      />
    );
  }
  if (status === "fail") {
    return (
      <XCircle
        className="h-3.5 w-3.5 text-(--qs-red)"
        aria-label={`${contextLabel} test failed`}
      />
    );
  }
  return null;
}

function WebhookChannelLabel({
  label,
  status,
  testedAt,
}: {
  label: string;
  status: WebhookTestResult | null | undefined;
  testedAt?: string | null;
}) {
  const testedLabel = formatTestedAgo(testedAt);
  return (
    <span className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">
      {label}
      <WebhookChannelStatusIcon status={status} contextLabel={label.replace(/ webhook URL$/i, "")} />
      {testedLabel && status ? (
        <span className="normal-case tracking-normal text-(--qs-text-4)">· Tested {testedLabel}</span>
      ) : null}
    </span>
  );
}

export const ExecutionStudioNotificationsPanel = memo(function ExecutionStudioNotificationsPanel({
  notifications,
  loading,
  onNotificationsChange,
  onError,
  onReloadOverview,
}: ExecutionStudioNotificationsPanelProps) {
  const [emailDraft, setEmailDraft] = useState("");
  const [slackWebhookDraft, setSlackWebhookDraft] = useState("");
  const [discordWebhookDraft, setDiscordWebhookDraft] = useState("");
  const [teamsWebhookDraft, setTeamsWebhookDraft] = useState("");
  const [telegramBotTokenDraft, setTelegramBotTokenDraft] = useState("");
  const [telegramChatIdDraft, setTelegramChatIdDraft] = useState("");
  const [notificationsBusy, setNotificationsBusy] = useState(false);
  const [webPushBusy, setWebPushBusy] = useState(false);
  const [webPushEnabled, setWebPushEnabled] = useState(false);
  const [webhookTestChannel, setWebhookTestChannel] = useState<WebhookChannel | "all" | null>(null);
  const [webhookTestStatus, setWebhookTestStatus] = useState<Partial<Record<WebhookChannel, WebhookTestResult>>>({});
  const [webhookTestTimestamps, setWebhookTestTimestamps] = useState<
    Partial<Record<WebhookTestChannelKey, string>>
  >({});
  const [emailTestBusy, setEmailTestBusy] = useState(false);
  const [emailTestStatus, setEmailTestStatus] = useState<WebhookTestResult | null>(null);
  const [digestPreviewOpen, setDigestPreviewOpen] = useState(false);
  const [digestPreviewBusy, setDigestPreviewBusy] = useState(false);
  const [digestPreviewSendBusy, setDigestPreviewSendBusy] = useState(false);
  const [digestPreviewSlack, setDigestPreviewSlack] = useState<string | null>(null);
  const [digestPreviewEmail, setDigestPreviewEmail] = useState<string | null>(null);
  const [digestPreviewMode, setDigestPreviewMode] = useState<"slack" | "email">("slack");
  const [digestSendWebhooks, setDigestSendWebhooks] = useState<Record<WebhookChannel, boolean>>({
    slack: true,
    discord: true,
    teams: true,
    telegram: true,
  });
  const [notificationSaveAcknowledged, setNotificationSaveAcknowledged] = useState(false);
  const [notificationSaveBannerDismissed, setNotificationSaveBannerDismissed] = useState(false);

  useEffect(() => {
    const recipients = notifications?.email_recipients ?? [];
    const emailValue = recipients.join(", ");
    const slackValue = notifications?.slack_webhook_url ?? "";
    const discordValue = notifications?.discord_webhook_url ?? "";
    const teamsValue = notifications?.teams_webhook_url ?? "";
    const telegramTokenValue = notifications?.telegram_bot_token ?? "";
    const telegramChatValue = notifications?.telegram_chat_id ?? "";
    setEmailDraft(emailValue);
    setSlackWebhookDraft(slackValue);
    setDiscordWebhookDraft(discordValue);
    setTeamsWebhookDraft(teamsValue);
    setTelegramBotTokenDraft(telegramTokenValue);
    setTelegramChatIdDraft(telegramChatValue);
    setWebPushEnabled(Boolean(notifications?.web_push_subscribed));

    const restored = loadWebhookTestStatus({
      slack: slackValue,
      discord: discordValue,
      teams: teamsValue,
      telegram: `${telegramTokenValue}|${telegramChatValue}`,
      email: emailValue,
    });
    const serverParsed = parseServerWebhookTestStatus(notifications?.webhook_test_status);
    setWebhookTestStatus({
      slack: serverParsed.statuses.slack ?? restored.slack,
      discord: serverParsed.statuses.discord ?? restored.discord,
      teams: serverParsed.statuses.teams ?? restored.teams,
      telegram: serverParsed.statuses.telegram ?? restored.telegram,
    });
    setWebhookTestTimestamps(serverParsed.timestamps);
    setEmailTestStatus(serverParsed.statuses.email ?? restored.email ?? null);
  }, [
    notifications?.discord_webhook_url,
    notifications?.email_recipients,
    notifications?.slack_webhook_url,
    notifications?.teams_webhook_url,
    notifications?.telegram_bot_token,
    notifications?.telegram_chat_id,
    notifications?.web_push_subscribed,
    notifications?.webhook_test_status,
  ]);

  const notificationSaveWarnings = useMemo(() => {
    const saved = notifications;
    if (!saved) {
      return [];
    }
    const warnings: string[] = [];
    if (
      webhookTestStatus.slack === "ok" &&
      slackWebhookDraft.trim() !== (saved.slack_webhook_url ?? "").trim()
    ) {
      warnings.push("Slack webhook URL changed since last successful test.");
    }
    if (
      webhookTestStatus.discord === "ok" &&
      discordWebhookDraft.trim() !== (saved.discord_webhook_url ?? "").trim()
    ) {
      warnings.push("Discord webhook URL changed since last successful test.");
    }
    if (
      webhookTestStatus.teams === "ok" &&
      teamsWebhookDraft.trim() !== (saved.teams_webhook_url ?? "").trim()
    ) {
      warnings.push("Teams webhook URL changed since last successful test.");
    }
    const savedTelegram = `${saved.telegram_bot_token ?? ""}|${saved.telegram_chat_id ?? ""}`.trim();
    const draftTelegram = `${telegramBotTokenDraft.trim()}|${telegramChatIdDraft.trim()}`.trim();
    if (webhookTestStatus.telegram === "ok" && draftTelegram !== savedTelegram) {
      warnings.push("Telegram bot token or chat id changed since last successful test.");
    }
    const savedEmails = (saved.email_recipients ?? []).join(", ");
    if (emailTestStatus === "ok" && emailDraft.trim() !== savedEmails.trim()) {
      warnings.push("Digest email recipients changed since last successful test.");
    }
    return warnings;
  }, [
    emailDraft,
    emailTestStatus,
    notifications,
    slackWebhookDraft,
    discordWebhookDraft,
    teamsWebhookDraft,
    telegramBotTokenDraft,
    telegramChatIdDraft,
    webhookTestStatus.discord,
    webhookTestStatus.slack,
    webhookTestStatus.teams,
    webhookTestStatus.telegram,
  ]);

  useEffect(() => {
    setNotificationSaveAcknowledged(false);
    setNotificationSaveBannerDismissed(false);
  }, [discordWebhookDraft, emailDraft, slackWebhookDraft, teamsWebhookDraft, telegramBotTokenDraft, telegramChatIdDraft]);

  const saveNotificationSettings = useCallback(async (force = false) => {
    if (notificationSaveWarnings.length > 0 && !force && !notificationSaveAcknowledged) {
      return;
    }

    setNotificationsBusy(true);
    onError(null);
    try {
      const email_recipients = emailDraft
        .split(/[,;\n]+/)
        .map((row) => row.trim())
        .filter(Boolean);
      const resp = await hivePatchJson<{ notifications: StudioNotifications }>("execution-studio/notifications", {
        email_recipients,
        slack_webhook_url: slackWebhookDraft.trim(),
        discord_webhook_url: discordWebhookDraft.trim(),
        teams_webhook_url: teamsWebhookDraft.trim(),
        telegram_bot_token: telegramBotTokenDraft.trim(),
        telegram_chat_id: telegramChatIdDraft.trim(),
      });
      onNotificationsChange(resp.notifications);
      setNotificationSaveAcknowledged(false);
      toast.success("Notification settings saved.");
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Notification settings update failed.");
    } finally {
      setNotificationsBusy(false);
    }
  }, [
    discordWebhookDraft,
    emailDraft,
    notificationSaveAcknowledged,
    notificationSaveWarnings.length,
    onError,
    onNotificationsChange,
    slackWebhookDraft,
    teamsWebhookDraft,
    telegramBotTokenDraft,
    telegramChatIdDraft,
  ]);

  const toggleWebPush = useCallback(async () => {
    setWebPushBusy(true);
    onError(null);
    try {
      if (webPushEnabled) {
        const ok = await unsubscribeExecutionStudioWebPush();
        setWebPushEnabled(!ok ? webPushEnabled : false);
        if (ok) setExecutionStudioPushIntent(false);
        toast.message(ok ? "Browser push disabled." : "Unable to disable browser push.");
      } else {
        const ok = await subscribeExecutionStudioWebPush();
        setWebPushEnabled(ok);
        if (ok) setExecutionStudioPushIntent(true);
        toast.success(ok ? "Browser push enabled for pending approvals." : "Browser push unavailable.");
      }
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Browser push update failed.");
    } finally {
      setWebPushBusy(false);
    }
  }, [onError, webPushEnabled]);

  const testNotificationWebhooks = useCallback(async (channel: WebhookChannel | "all") => {
    const slack = slackWebhookDraft.trim();
    const discord = discordWebhookDraft.trim();
    const teams = teamsWebhookDraft.trim();
    const telegramToken = telegramBotTokenDraft.trim();
    const telegramChatId = telegramChatIdDraft.trim();
    const telegramFingerprint = `${telegramToken}|${telegramChatId}`;

    if ((channel === "slack" || channel === "all") && slack && !slack.startsWith("https://hooks.slack.com/")) {
      toast.error("Slack potrebuje webhook URL (https://hooks.slack.com/…), nie email. Email daj hore do Digest emails.");
      return;
    }
    if ((channel === "discord" || channel === "all") && discord && !discord.startsWith("https://discord.com/api/webhooks/")) {
      toast.error("Discord webhook musí začínať https://discord.com/api/webhooks/…");
      return;
    }
    if ((channel === "teams" || channel === "all") && teams && !teams.startsWith("https://")) {
      toast.error("Teams webhook musí byť platná https:// URL z Microsoft Teams.");
      return;
    }
    if ((channel === "telegram" || channel === "all") && telegramToken && !telegramToken.includes(":")) {
      toast.error("Telegram bot token z @BotFather má formát 123456789:ABC…");
      return;
    }
    if ((channel === "telegram" || channel === "all") && telegramToken && !telegramChatId) {
      toast.error("Telegram potrebuje aj Chat ID — napíš botovi /start v Telegrame.");
      return;
    }

    setWebhookTestChannel(channel);
    onError(null);
    try {
      const saved = await hivePatchJson<{ notifications: StudioNotifications }>("execution-studio/notifications", {
        email_recipients: emailDraft
          .split(/[,;\n]+/)
          .map((row) => row.trim())
          .filter(Boolean),
        slack_webhook_url: slack,
        discord_webhook_url: discord,
        teams_webhook_url: teams,
        telegram_bot_token: telegramToken,
        telegram_chat_id: telegramChatId,
      });
      onNotificationsChange(saved.notifications);

      const resp = await hivePostJson<{
        detail?: string;
        slack?: boolean;
        discord?: boolean;
        teams?: boolean;
        telegram?: boolean;
      }>("execution-studio/notifications/test-webhooks", channel === "all" ? {} : { channels: [channel] });
      const applyStatus = (key: WebhookChannel, ok: boolean) => {
        const status: WebhookTestResult = ok ? "ok" : "fail";
        const testedAt = new Date().toISOString();
        setWebhookTestStatus((prev) => ({ ...prev, [key]: status }));
        setWebhookTestTimestamps((prev) => ({ ...prev, [key]: testedAt }));
        const value =
          key === "slack"
            ? slackWebhookDraft
            : key === "discord"
              ? discordWebhookDraft
              : key === "teams"
                ? teamsWebhookDraft
                : telegramFingerprint;
        saveWebhookTestStatus(key, value, status);
      };

      if (resp.detail === "no_webhooks_accepted") {
        if (channel === "all") {
          applyStatus("slack", false);
          applyStatus("discord", false);
          applyStatus("teams", false);
          applyStatus("telegram", false);
        } else {
          applyStatus(channel, false);
        }
        toast.message(
          channel === "slack"
            ? "Slack test zlyhal — skontroluj webhook URL alebo nechaj pole prázdne."
            : channel === "discord"
              ? "Discord test zlyhal — webhook môže byť neplatný alebo zmazaný v Discorde."
              : channel === "teams"
                ? "Teams test zlyhal — skontroluj incoming webhook URL."
                : channel === "telegram"
                  ? "Telegram test zlyhal — skontroluj bot token, chat id a či si botovi poslal /start."
                  : "Webhook test zlyhal — skontroluj URL a najprv ulož nastavenia.",
        );
        return;
      }

      if (channel === "all") {
        applyStatus("slack", Boolean(resp.slack));
        applyStatus("discord", Boolean(resp.discord));
        applyStatus("teams", Boolean(resp.teams));
        applyStatus("telegram", Boolean(resp.telegram));
      } else {
        applyStatus(channel, Boolean(resp[channel]));
      }

      const label =
        channel === "all"
          ? [
              resp.slack ? "Slack" : null,
              resp.discord ? "Discord" : null,
              resp.teams ? "Teams" : null,
              resp.telegram ? "Telegram" : null,
            ]
              .filter(Boolean)
              .join(", ")
          : channel.charAt(0).toUpperCase() + channel.slice(1);
      toast.success(label ? `${label} notification test sent.` : "Notification test completed.");
    } catch (exc) {
      if (channel === "all") {
        setWebhookTestStatus({ slack: "fail", discord: "fail", teams: "fail", telegram: "fail" });
        saveWebhookTestStatus("slack", slackWebhookDraft, "fail");
        saveWebhookTestStatus("discord", discordWebhookDraft, "fail");
        saveWebhookTestStatus("teams", teamsWebhookDraft, "fail");
        saveWebhookTestStatus("telegram", telegramFingerprint, "fail");
      } else {
        setWebhookTestStatus((prev) => ({ ...prev, [channel]: "fail" }));
        const value =
          channel === "slack"
            ? slackWebhookDraft
            : channel === "discord"
              ? discordWebhookDraft
              : channel === "teams"
                ? teamsWebhookDraft
                : telegramFingerprint;
        saveWebhookTestStatus(channel, value, "fail");
      }
      onError(exc instanceof HiveApiError ? exc.message : "Webhook test failed.");
    } finally {
      setWebhookTestChannel(null);
    }
  }, [
    discordWebhookDraft,
    emailDraft,
    onError,
    onNotificationsChange,
    slackWebhookDraft,
    teamsWebhookDraft,
    telegramBotTokenDraft,
    telegramChatIdDraft,
  ]);

  const testDigestEmail = useCallback(async () => {
    const recipients = emailDraft
      .split(/[,;\n]+/)
      .map((row) => row.trim())
      .filter(Boolean);
    if (recipients.length === 0) {
      toast.error("Pridaj aspoň jeden email do Digest emails a potom klikni Test.");
      return;
    }

    setEmailTestBusy(true);
    onError(null);
    try {
      const saved = await hivePatchJson<{ notifications: StudioNotifications }>("execution-studio/notifications", {
        email_recipients: recipients,
        slack_webhook_url: slackWebhookDraft.trim(),
        discord_webhook_url: discordWebhookDraft.trim(),
        teams_webhook_url: teamsWebhookDraft.trim(),
        telegram_bot_token: telegramBotTokenDraft.trim(),
        telegram_chat_id: telegramChatIdDraft.trim(),
      });
      onNotificationsChange(saved.notifications);

      const resp = await hivePostJson<{ detail?: string; sent?: boolean; recipient_count?: number }>(
        "execution-studio/notifications/test-email",
        {},
      );
      if (!resp.sent) {
        setEmailTestStatus("fail");
        saveWebhookTestStatus("email", emailDraft, "fail");
        toast.message(
          resp.detail === "no_recipients"
            ? "Pridaj digest email a skús znova."
            : resp.detail === "smtp_not_configured"
              ? "Email sa neodosiela — na serveri chýba SMTP (SMTP_USER + SMTP_PASS v .env.prod)."
              : "Digest email sa nepodarilo doručiť — skontroluj SMTP alebo spam.",
        );
        return;
      }
      setEmailTestStatus("ok");
      setWebhookTestTimestamps((prev) => ({ ...prev, email: new Date().toISOString() }));
      saveWebhookTestStatus("email", emailDraft, "ok");
      toast.success(
        resp.recipient_count
          ? `Digest test email sent to ${resp.recipient_count} recipient(s).`
          : "Digest test email sent.",
      );
    } catch (exc) {
      setEmailTestStatus("fail");
      saveWebhookTestStatus("email", emailDraft, "fail");
      onError(exc instanceof HiveApiError ? exc.message : "Digest email test failed.");
    } finally {
      setEmailTestBusy(false);
    }
  }, [
    discordWebhookDraft,
    emailDraft,
    onError,
    onNotificationsChange,
    slackWebhookDraft,
    teamsWebhookDraft,
    telegramBotTokenDraft,
    telegramChatIdDraft,
  ]);

  const loadDigestPreview = useCallback(async () => {
    setDigestPreviewBusy(true);
    onError(null);
    try {
      const resp = await hiveGet<{
        message?: string;
        email_body?: string;
        last_sent_at?: string | null;
      }>("execution-studio/notifications/weekly-rollup-preview");
      setDigestPreviewSlack(resp.message ?? null);
      setDigestPreviewEmail(resp.email_body ?? resp.message ?? null);
      setDigestPreviewMode("slack");
      setDigestPreviewOpen(true);
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Weekly digest preview failed.");
    } finally {
      setDigestPreviewBusy(false);
    }
  }, [onError]);

  const sendDigestPreview = useCallback(async () => {
    setDigestPreviewSendBusy(true);
    onError(null);
    try {
      const channels =
        digestPreviewMode === "email"
          ? (["email"] as const)
          : (["slack", "discord", "teams", "telegram"] as const).filter((ch) => digestSendWebhooks[ch]);
      if (channels.length === 0) {
        toast.message("Select at least one webhook channel to send.");
        return;
      }
      const resp = await hivePostJson<{ ok?: boolean; detail?: string; channels?: Record<string, boolean> }>(
        "execution-studio/notifications/send-weekly-rollup-preview",
        { channels: [...channels] },
      );
      if (!resp.ok) {
        toast.message(
          resp.detail === "no_channels_delivered"
            ? "Selected channels are not configured or rejected the message."
            : "Weekly digest preview could not be delivered.",
        );
        return;
      }
      toast.success(`Weekly digest preview sent (${channels.join(", ")}).`);
      await onReloadOverview();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Weekly digest preview send failed.");
    } finally {
      setDigestPreviewSendBusy(false);
    }
  }, [digestPreviewMode, digestSendWebhooks, onError, onReloadOverview]);

  return (
    <div className="qs-bubble shrink-0 p-4">
      <p className="text-sm font-semibold text-(--qs-text)">Operator notifications</p>
      <p className="mt-1 text-xs text-(--qs-text-3)">
        Weekly rollup emails plus Slack, Discord, Teams, and Telegram for pending approvals. Empty fields fall back to audit digest settings.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={digestPreviewBusy || loading}
          aria-label="Preview weekly digest"
          onClick={() => void loadDigestPreview()}
        >
          {digestPreviewBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Preview weekly digest"}
        </button>
        {notifications?.last_weekly_rollup_at ? (
          <span className="text-[10px] text-(--qs-text-4)">
            Last sent {new Date(notifications.last_weekly_rollup_at).toLocaleString()}
          </span>
        ) : null}
        <V4Badge tone={notifications?.weekly_rollup_enabled ? "ok" : "warn"}>
          {notifications?.weekly_rollup_enabled ? "Weekly rollup scheduled" : "Weekly rollup off"}
        </V4Badge>
      </div>
      {digestPreviewOpen && (digestPreviewSlack || digestPreviewEmail) ? (
        <div
          className="qs-bubble-inner mt-2 max-h-56 overflow-auto p-3"
          aria-label="Weekly digest preview"
        >
          <div className="mb-2 flex gap-2">
            <button
              type="button"
              className={cn(
                "qs-btn qs-btn--ghost qs-btn--sm",
                digestPreviewMode === "slack" && "ring-1 ring-cyan/40",
              )}
              onClick={() => setDigestPreviewMode("slack")}
            >
              Slack
            </button>
            <button
              type="button"
              className={cn(
                "qs-btn qs-btn--ghost qs-btn--sm",
                digestPreviewMode === "email" && "ring-1 ring-cyan/40",
              )}
              onClick={() => setDigestPreviewMode("email")}
            >
              Email
            </button>
            {digestPreviewMode === "slack" ? (
              <div className="flex flex-wrap items-center gap-2 text-[10px] text-(--qs-text-3)">
                {(["slack", "discord", "teams", "telegram"] as const).map((ch) => (
                  <label key={ch} className="inline-flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={digestSendWebhooks[ch]}
                      onChange={(event) =>
                        setDigestSendWebhooks((prev) => ({ ...prev, [ch]: event.target.checked }))
                      }
                    />
                    {ch.charAt(0).toUpperCase() + ch.slice(1)}
                  </label>
                ))}
              </div>
            ) : null}
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm ml-auto"
              disabled={digestPreviewSendBusy || notificationsBusy || loading}
              aria-label="Send weekly digest preview"
              onClick={() => void sendDigestPreview()}
            >
              {digestPreviewSendBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : digestPreviewMode === "slack" ? (
                "Send selected"
              ) : (
                "Send to email"
              )}
            </button>
          </div>
          {digestPreviewMode === "slack" && digestPreviewSlack ? (
            <SlackMarkdownPreview content={digestPreviewSlack} />
          ) : (
            <pre className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-(--qs-text-2)">
              {digestPreviewEmail ?? digestPreviewSlack ?? "No preview available."}
            </pre>
          )}
        </div>
      ) : null}
      <span className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">
        Digest emails
        <WebhookChannelStatusIcon status={emailTestStatus} contextLabel="Digest email" />
        {formatTestedAgo(webhookTestTimestamps.email) && emailTestStatus ? (
          <span className="normal-case tracking-normal text-(--qs-text-4)">
            · Tested {formatTestedAgo(webhookTestTimestamps.email)}
          </span>
        ) : null}
      </span>
      <div className="mt-1 flex gap-2">
        <textarea
          className="v4-input min-h-[4.5rem] min-w-0 flex-1 font-mono text-xs"
          value={emailDraft}
          disabled={notificationsBusy || loading}
          placeholder="ops@example.com, lead@example.com"
          onChange={(event) => {
            setEmailDraft(event.target.value);
            setEmailTestStatus(null);
            setWebhookTestTimestamps((prev) => {
              const next = { ...prev };
              delete next.email;
              return next;
            });
            clearWebhookTestStatusChannel("email");
          }}
        />
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 self-start"
          disabled={emailTestBusy || notificationsBusy || loading}
          aria-label="Test digest email"
          onClick={() => void testDigestEmail()}
        >
          {emailTestBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Test"}
        </button>
      </div>
      <WebhookChannelLabel
        label="Slack webhook URL"
        status={webhookTestStatus.slack}
        testedAt={webhookTestTimestamps.slack}
      />
      <div className="mt-1 flex gap-2">
        <input
          type="url"
          className="v4-input min-w-0 flex-1 font-mono text-xs"
          value={slackWebhookDraft}
          disabled={notificationsBusy || loading}
          placeholder="https://hooks.slack.com/services/..."
          onChange={(event) => {
            setSlackWebhookDraft(event.target.value);
            setWebhookTestStatus((prev) => {
              const next = { ...prev };
              delete next.slack;
              return next;
            });
            setWebhookTestTimestamps((prev) => {
              const next = { ...prev };
              delete next.slack;
              return next;
            });
            clearWebhookTestStatusChannel("slack");
          }}
        />
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
          disabled={webhookTestChannel !== null || notificationsBusy || loading}
          aria-label="Test Slack webhook"
          onClick={() => void testNotificationWebhooks("slack")}
        >
          {webhookTestChannel === "slack" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Test"}
        </button>
      </div>
      <WebhookChannelLabel
        label="Discord webhook URL"
        status={webhookTestStatus.discord}
        testedAt={webhookTestTimestamps.discord}
      />
      <div className="mt-1 flex gap-2">
        <input
          type="url"
          className="v4-input min-w-0 flex-1 font-mono text-xs"
          value={discordWebhookDraft}
          disabled={notificationsBusy || loading}
          placeholder="https://discord.com/api/webhooks/..."
          onChange={(event) => {
            setDiscordWebhookDraft(event.target.value);
            setWebhookTestStatus((prev) => {
              const next = { ...prev };
              delete next.discord;
              return next;
            });
            setWebhookTestTimestamps((prev) => {
              const next = { ...prev };
              delete next.discord;
              return next;
            });
            clearWebhookTestStatusChannel("discord");
          }}
        />
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
          disabled={webhookTestChannel !== null || notificationsBusy || loading}
          aria-label="Test Discord webhook"
          onClick={() => void testNotificationWebhooks("discord")}
        >
          {webhookTestChannel === "discord" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Test"}
        </button>
      </div>
      <WebhookChannelLabel
        label="Microsoft Teams webhook URL"
        status={webhookTestStatus.teams}
        testedAt={webhookTestTimestamps.teams}
      />
      <div className="mt-1 flex gap-2">
        <input
          type="url"
          className="v4-input min-w-0 flex-1 font-mono text-xs"
          value={teamsWebhookDraft}
          disabled={notificationsBusy || loading}
          placeholder="https://outlook.office.com/webhook/..."
          onChange={(event) => {
            setTeamsWebhookDraft(event.target.value);
            setWebhookTestStatus((prev) => {
              const next = { ...prev };
              delete next.teams;
              return next;
            });
            setWebhookTestTimestamps((prev) => {
              const next = { ...prev };
              delete next.teams;
              return next;
            });
            clearWebhookTestStatusChannel("teams");
          }}
        />
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
          disabled={webhookTestChannel !== null || notificationsBusy || loading}
          aria-label="Test Teams webhook"
          onClick={() => void testNotificationWebhooks("teams")}
        >
          {webhookTestChannel === "teams" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Test"}
        </button>
      </div>
      <WebhookChannelLabel
        label="Telegram bot token"
        status={webhookTestStatus.telegram}
        testedAt={webhookTestTimestamps.telegram}
      />
      <div className="mt-1 flex gap-2">
        <input
          type="password"
          autoComplete="off"
          className="v4-input min-w-0 flex-1 font-mono text-xs"
          value={telegramBotTokenDraft}
          disabled={notificationsBusy || loading}
          placeholder="123456789:ABC… from @BotFather"
          onChange={(event) => {
            setTelegramBotTokenDraft(event.target.value);
            setWebhookTestStatus((prev) => {
              const next = { ...prev };
              delete next.telegram;
              return next;
            });
            setWebhookTestTimestamps((prev) => {
              const next = { ...prev };
              delete next.telegram;
              return next;
            });
            clearWebhookTestStatusChannel("telegram");
          }}
        />
      </div>
      <WebhookChannelLabel label="Telegram chat ID" status={null} testedAt={null} />
      <div className="mt-1 flex gap-2">
        <input
          type="text"
          className="v4-input min-w-0 flex-1 font-mono text-xs"
          value={telegramChatIdDraft}
          disabled={notificationsBusy || loading}
          placeholder="Your chat id (send /start to @QueenSwarm_bot first)"
          onChange={(event) => {
            setTelegramChatIdDraft(event.target.value);
            setWebhookTestStatus((prev) => {
              const next = { ...prev };
              delete next.telegram;
              return next;
            });
            setWebhookTestTimestamps((prev) => {
              const next = { ...prev };
              delete next.telegram;
              return next;
            });
            clearWebhookTestStatusChannel("telegram");
          }}
        />
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
          disabled={webhookTestChannel !== null || notificationsBusy || loading}
          aria-label="Test Telegram bot"
          onClick={() => void testNotificationWebhooks("telegram")}
        >
          {webhookTestChannel === "telegram" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : "Test"}
        </button>
      </div>
      {notifications?.web_push_configured ? (
        <label className="qs-bubble-inner mt-3 flex items-center justify-between gap-3 px-3 py-2 text-xs text-(--qs-text-2)">
          <span>Browser push for pending approvals</span>
          <HiveSwitch
            checked={webPushEnabled}
            disabled={webPushBusy || loading}
            onCheckedChange={() => void toggleWebPush()}
          />
        </label>
      ) : (
        <p className="mt-3 text-[10px] text-(--qs-text-4)">
          Browser push is not configured on this deployment (VAPID keys missing).
        </p>
      )}
      {notificationSaveWarnings.length > 0 && !notificationSaveAcknowledged && !notificationSaveBannerDismissed ? (
        <div
          className="qs-bubble qs-bubble--tint-amber mt-3 p-3 text-xs text-(--qs-text-2)"
          role="status"
          aria-label="Notification settings change warning"
        >
          <p className="font-semibold text-pollen">Verified fields changed</p>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-(--qs-text-3)">
            {notificationSaveWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] text-(--qs-text-4)">
            Saving will clear test status for changed webhook or email fields.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={notificationsBusy}
              onClick={() => {
                setNotificationSaveAcknowledged(true);
                void saveNotificationSettings(true);
              }}
            >
              Save anyway
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => setNotificationSaveBannerDismissed(true)}
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}
      {(notifications?.webhook_test_history?.length ?? 0) > 0 ? (
        <details className="mt-3 text-xs text-(--qs-text-3)">
          <summary className="cursor-pointer text-(--qs-text-2)">Webhook test history</summary>
          <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto hive-scrollbar">
            {notifications?.webhook_test_history?.map((row, index) => (
              <li
                key={`${row.channel}-${row.tested_at ?? index}`}
                className="qs-bubble-inner flex flex-wrap items-center justify-between gap-2 px-2 py-1"
              >
                <span className="font-mono text-[10px] uppercase text-(--qs-text-4)">{row.channel}</span>
                <span className={row.status === "ok" ? "text-verified" : "text-(--qs-red)"}>{row.status}</span>
                <span className="text-[10px] text-(--qs-text-4)">
                  {row.tested_at ? formatTestedAgo(row.tested_at) ?? new Date(row.tested_at).toLocaleString() : "—"}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <div className="mt-2 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={webhookTestChannel !== null || notificationsBusy || loading}
          onClick={() => void testNotificationWebhooks("all")}
        >
          {webhookTestChannel === "all" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          Test all webhooks
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={
            notificationsBusy ||
            loading ||
            (notificationSaveWarnings.length > 0 && !notificationSaveAcknowledged && !notificationSaveBannerDismissed)
          }
          onClick={() => void saveNotificationSettings()}
        >
          {notificationsBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          Save notification settings
        </button>
      </div>
    </div>
  );
});
