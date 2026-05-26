/** Human-readable relative time for webhook test timestamps. */
export function formatTestedAgo(iso: string | null | undefined): string | null {
  if (!iso?.trim()) {
    return null;
  }
  const testedMs = new Date(iso).getTime();
  if (Number.isNaN(testedMs)) {
    return null;
  }
  const deltaMs = Date.now() - testedMs;
  if (deltaMs < 60_000) {
    return "just now";
  }
  const minutes = Math.floor(deltaMs / 60_000);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
