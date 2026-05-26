import { describe, expect, it, beforeEach } from "vitest";

import {
  clearWebhookTestStatusChannel,
  loadWebhookTestStatus,
  saveWebhookTestStatus,
  webhookTestFingerprint,
} from "@/lib/execution-studio-webhook-test-status";

function installLocalStorageMock(): void {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => {
        store.clear();
      },
    },
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: globalThis,
  });
}

describe("execution studio webhook test status", () => {
  beforeEach(() => {
    installLocalStorageMock();
  });

  it("persists and restores status when fingerprint matches", () => {
    saveWebhookTestStatus("slack", "https://hooks.slack.com/services/abc", "ok");
    const restored = loadWebhookTestStatus({
      slack: "https://hooks.slack.com/services/abc",
    });
    expect(restored.slack).toBe("ok");
  });

  it("drops restored status when fingerprint changes", () => {
    saveWebhookTestStatus("email", "ops@example.com", "ok");
    const restored = loadWebhookTestStatus({ email: "lead@example.com" });
    expect(restored.email).toBeUndefined();
  });

  it("clears one channel without affecting others", () => {
    saveWebhookTestStatus("slack", "https://hooks.slack.com/a", "ok");
    saveWebhookTestStatus("discord", "https://discord.com/api/webhooks/1", "fail");
    clearWebhookTestStatusChannel("slack");
    const restored = loadWebhookTestStatus({
      slack: "https://hooks.slack.com/a",
      discord: "https://discord.com/api/webhooks/1",
    });
    expect(restored.slack).toBeUndefined();
    expect(restored.discord).toBe("fail");
  });

  it("fingerprints long values from the tail", () => {
    const long = `https://hooks.slack.com/services/${"x".repeat(80)}`;
    expect(webhookTestFingerprint(long).length).toBeLessThanOrEqual(48);
  });
});
