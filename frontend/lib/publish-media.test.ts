/** Vitest — publish media URL client guards. */

import { describe, expect, it } from "vitest";

import {
  classifyPublishMediaUrl,
  isSafePublishMediaUrl,
  resolvePublishMediaPreviewMode,
} from "@/lib/publish-media";

describe("publish-media", () => {
  it("accepts public HTTPS URLs", () => {
    expect(isSafePublishMediaUrl("https://cdn.example.com/post.jpg")).toBe(true);
  });

  it("rejects http and localhost", () => {
    expect(isSafePublishMediaUrl("http://cdn.example.com/x.jpg")).toBe(false);
    expect(isSafePublishMediaUrl("https://localhost/x.jpg")).toBe(false);
  });

  it("classifies image and video extensions", () => {
    expect(classifyPublishMediaUrl("https://cdn.example.com/a.png")).toBe("image");
    expect(classifyPublishMediaUrl("https://cdn.example.com/reel.mp4")).toBe("video");
  });

  it("resolves tiktok channel to video preview mode", () => {
    expect(
      resolvePublishMediaPreviewMode("https://cdn.example.com/reel.mp4", "tiktok"),
    ).toBe("video");
  });

  it("falls back to link for unsafe URLs", () => {
    expect(resolvePublishMediaPreviewMode("http://bad.local/x.jpg")).toBe("link");
  });
});
