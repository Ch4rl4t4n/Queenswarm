import { describe, expect, it } from "vitest";

import {
  hivePageShellAgentsSync,
  hivePageShellError,
  hivePageShellErrorFirst,
  hivePageShellNotice,
} from "@/lib/hive-page-error";

describe("hive-page-error", () => {
  it("returns null for empty messages", () => {
    expect(hivePageShellError(null)).toBeNull();
    expect(hivePageShellError("   ")).toBeNull();
  });

  it("maps trimmed message with optional dismiss", () => {
    const onDismiss = (): void => undefined;
    expect(hivePageShellError("  proxy failed  ", onDismiss)).toEqual({
      message: "proxy failed",
      tone: "error",
      onDismiss,
      onRetry: undefined,
      retryBusy: undefined,
      testId: undefined,
    });
  });

  it("supports retry options object", () => {
    const onRetry = (): void => undefined;
    expect(
      hivePageShellError("upstream failed", {
        onRetry,
        retryBusy: true,
        testId: "agents-sync-banner",
      }),
    ).toEqual({
      message: "upstream failed",
      tone: "error",
      onDismiss: undefined,
      onRetry,
      retryBusy: true,
      testId: "agents-sync-banner",
    });
  });

  it("maps warn notices", () => {
    expect(hivePageShellNotice("syncing…")).toEqual({
      message: "syncing…",
      tone: "warn",
      onDismiss: undefined,
      onRetry: undefined,
      retryBusy: undefined,
      testId: undefined,
    });
  });

  it("picks first non-empty error from list", () => {
    expect(hivePageShellErrorFirst([null, "", "swarm sync failed"])).toEqual({
      message: "swarm sync failed",
      tone: "error",
      onDismiss: undefined,
      onRetry: undefined,
      retryBusy: undefined,
      testId: undefined,
    });
  });

  it("agents sync prefers fetch errors over pending warn", () => {
    expect(
      hivePageShellAgentsSync({
        rosterError: "Roster unreachable",
        swarmsError: null,
        rosterSyncPending: true,
      }),
    ).toMatchObject({
      message: "Roster unreachable",
      tone: "error",
      testId: "agents-sync-banner",
    });
  });

  it("agents sync shows pending notice when no fetch error", () => {
    expect(
      hivePageShellAgentsSync({
        rosterError: null,
        swarmsError: null,
        rosterSyncPending: true,
      }),
    ).toMatchObject({
      tone: "warn",
      testId: "agents-sync-banner",
    });
  });
});
