export function runtimeModeLabel(mode: string): string {
  const key = mode.trim().toLowerCase();
  if (key === "durable") return "durable";
  return "in-process";
}

export function isTerminalSessionStatus(status: string): boolean {
  const key = status.trim().toLowerCase();
  return key === "completed" || key === "failed" || key === "stopped";
}

