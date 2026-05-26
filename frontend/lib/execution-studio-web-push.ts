"use client";

import { hiveDeleteJson, hiveGet, hivePostJson } from "@/lib/api";

interface PushSubscribeResponse {
  ok: boolean;
  enabled: boolean;
}

function urlBase64ToUint8Array(base64String: string): BufferSource {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output.buffer.slice(output.byteOffset, output.byteOffset + output.byteLength);
}

/** Fetch VAPID public key when server push is configured. */
export async function fetchExecutionStudioVapidPublicKey(): Promise<string | null> {
  try {
    const payload = await hiveGet<{ configured: boolean; public_key?: string | null }>(
      "execution-studio/push/vapid-public-key",
    );
    if (!payload.configured || !payload.public_key) return null;
    return payload.public_key;
  } catch {
    return null;
  }
}

/** Subscribe browser to Execution Studio pending push alerts. */
export async function subscribeExecutionStudioWebPush(): Promise<boolean> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return false;
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return false;
  }

  const publicKey = await fetchExecutionStudioVapidPublicKey();
  if (!publicKey) {
    return false;
  }

  const registration = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  await navigator.serviceWorker.ready;

  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    }));

  const json = subscription.toJSON();
  const resp = await hivePostJson<PushSubscribeResponse>("execution-studio/push/subscribe", {
    subscription: json,
  });
  return resp.ok && resp.enabled;
}

/** Unsubscribe browser push for Execution Studio pending alerts. */
export async function unsubscribeExecutionStudioWebPush(): Promise<boolean> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return false;
  }
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (subscription) {
    await subscription.unsubscribe();
  }
  const resp = await hiveDeleteJson<PushSubscribeResponse>("execution-studio/push/subscribe");
  return resp.ok;
}
