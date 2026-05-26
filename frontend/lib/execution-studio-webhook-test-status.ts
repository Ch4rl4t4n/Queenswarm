"use client";

export type WebhookTestResult = "ok" | "fail";
export type WebhookTestChannel = "slack" | "discord" | "teams" | "telegram" | "email";

interface StoredChannelStatus {
  fingerprint: string;
  status: WebhookTestResult;
}

interface StoredWebhookTestPayload {
  channels: Partial<Record<WebhookTestChannel, StoredChannelStatus>>;
}

const STORAGE_KEY = "qs_execution_studio_webhook_test_status";

function readPayload(): StoredWebhookTestPayload {
  if (typeof window === "undefined") {
    return { channels: {} };
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { channels: {} };
    }
    const parsed = JSON.parse(raw) as StoredWebhookTestPayload;
    if (!parsed || typeof parsed !== "object" || !parsed.channels) {
      return { channels: {} };
    }
    return parsed;
  } catch {
    return { channels: {} };
  }
}

function writePayload(payload: StoredWebhookTestPayload): void {
  if (typeof window === "undefined") {
    return;
  }
  if (Object.keys(payload.channels).length === 0) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

/** Fingerprint notification field values so persisted status survives refresh. */
export function webhookTestFingerprint(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.length <= 48 ? trimmed : trimmed.slice(-48);
}

/** Restore channel test icons when stored fingerprints still match current drafts. */
export function loadWebhookTestStatus(
  fingerprints: Partial<Record<WebhookTestChannel, string>>,
): Partial<Record<WebhookTestChannel, WebhookTestResult>> {
  const payload = readPayload();
  const out: Partial<Record<WebhookTestChannel, WebhookTestResult>> = {};
  for (const channel of ["slack", "discord", "teams", "telegram", "email"] as const) {
    const fp = webhookTestFingerprint(fingerprints[channel] ?? "");
    const stored = payload.channels[channel];
    if (fp && stored?.fingerprint === fp && stored.status) {
      out[channel] = stored.status;
    }
  }
  return out;
}

/** Persist one channel test result keyed by its URL/email fingerprint. */
export function saveWebhookTestStatus(
  channel: WebhookTestChannel,
  value: string,
  status: WebhookTestResult,
): void {
  const fingerprint = webhookTestFingerprint(value);
  if (!fingerprint) {
    return;
  }
  const payload = readPayload();
  payload.channels[channel] = { fingerprint, status };
  writePayload(payload);
}

/** Drop persisted status when operator edits the underlying field. */
export function clearWebhookTestStatusChannel(channel: WebhookTestChannel): void {
  const payload = readPayload();
  delete payload.channels[channel];
  writePayload(payload);
}
