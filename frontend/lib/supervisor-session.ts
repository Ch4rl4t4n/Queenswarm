export function runtimeModeLabel(mode: string): string {
  const key = mode.trim().toLowerCase();
  if (key === "durable") return "durable";
  return "in-process";
}

export function isTerminalSessionStatus(status: string): boolean {
  const key = status.trim().toLowerCase();
  return key === "completed" || key === "failed" || key === "stopped";
}

export function sessionStatusTone(status: string): "amber" | "cyan" | "green" | "magenta" | "red" {
  const key = status.trim().toLowerCase();
  if (key === "completed") return "green";
  if (key === "needs_input") return "magenta";
  if (key === "failed" || key === "stopped") return "red";
  if (key === "running") return "cyan";
  return "amber";
}

