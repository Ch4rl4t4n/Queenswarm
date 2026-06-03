import { formatTimeAgoIso } from "@/lib/format-relative-time";

/** Human-readable relative time for webhook test timestamps. */
export function formatTestedAgo(iso: string | null | undefined): string | null {
  if (!iso?.trim()) {
    return null;
  }
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return null;
  }
  const sec = Math.floor((Date.now() - parsed) / 1000);
  if (sec < 60) {
    return "just now";
  }
  return formatTimeAgoIso(iso, { justNowBelowSec: 0 });
}
