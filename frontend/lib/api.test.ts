import { afterEach, describe, expect, it, vi } from "vitest";

import { HiveApiError, hiveApiUserMessage, hiveGet, hivePostJson, isRateLimitError } from "@/lib/api";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
  },
}));

describe("hive api proxy wrapper", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses /api/proxy and includes credentials for session auth", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const out = await hiveGet<{ ok: boolean }>("foragers");

    expect(out.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/proxy/foragers",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
        cache: "no-store",
      }),
    );
  });

  it("throws HiveApiError with backend detail from proxy response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Tenant context missing." }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );

    try {
      await hivePostJson("foragers", { name: "x" });
      throw new Error("Expected hivePostJson to throw HiveApiError.");
    } catch (error: unknown) {
      expect(error).toBeInstanceOf(HiveApiError);
      const typed = error as HiveApiError;
      expect(typed.name).toBe("HiveApiError");
      expect(typed.message).toBe("Tenant context missing.");
      expect(typed.status).toBe(403);
    }
  });

  it("retries 429 responses using Retry-After then succeeds", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Rate limit exceeded." }), {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "1" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    const out = await hiveGet<{ ok: boolean }>("dashboard/summary");
    expect(out.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("throws HiveApiError after exhausting 429 retries", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Rate limit exceeded." }), {
        status: 429,
        headers: { "Content-Type": "application/json", "Retry-After": "1" },
      }),
    );

    await expect(hiveGet("dashboard/summary")).rejects.toMatchObject({
      status: 429,
      message: "Rate limit reached — wait a few seconds and try again.",
    });
  });

  it("isRateLimitError and hiveApiUserMessage helpers", () => {
    const err = new HiveApiError("Rate limit exceeded.", 429, {});
    expect(isRateLimitError(err)).toBe(true);
    expect(hiveApiUserMessage(err)).toContain("Rate limit");
    expect(isRateLimitError(new HiveApiError("nope", 500, {}))).toBe(false);
  });
});
