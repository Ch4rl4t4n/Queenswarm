import { describe, expect, it } from "vitest";

import { isTerminalSessionStatus, runtimeModeLabel, sessionStatusTone } from "./supervisor-session";

describe("supervisor-session helpers", () => {
  it("maps runtime mode labels", () => {
    expect(runtimeModeLabel("durable")).toBe("durable");
    expect(runtimeModeLabel("inprocess")).toBe("in-process");
    expect(runtimeModeLabel("unknown")).toBe("in-process");
  });

  it("detects terminal statuses", () => {
    expect(isTerminalSessionStatus("completed")).toBe(true);
    expect(isTerminalSessionStatus("stopped")).toBe(true);
    expect(isTerminalSessionStatus("running")).toBe(false);
  });

  it("maps session status tones", () => {
    expect(sessionStatusTone("running")).toBe("cyan");
    expect(sessionStatusTone("needs_input")).toBe("magenta");
    expect(sessionStatusTone("completed")).toBe("green");
  });
});

