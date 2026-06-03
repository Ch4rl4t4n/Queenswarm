/** Command Center–style relative time: s → m → h → d with automatic scaling. */

const SEC_MIN = 60;
const SEC_HOUR = 3600;
const SEC_DAY = 86_400;

export type FormatRelativeTimeStyle = "compact" | "verbose";

export interface FormatDurationSecondsOptions {
  /** Single largest unit (3.3d, 4h) vs compound under 1h (12m 5s). Default compact. */
  style?: FormatRelativeTimeStyle;
  suffix?: "ago" | "none";
  /** When set with suffix "ago", values below this show "just now". */
  justNowBelowSec?: number;
}

function withSuffix(value: string, suffix: "ago" | "none"): string {
  return suffix === "ago" ? `${value} ago` : value;
}

/**
 * Format a duration in seconds using the largest readable unit.
 *
 * Examples: 45s · 12m · 1.0h · 7.1d (matches Command Center KPI cards).
 */
export function formatDurationSeconds(
  totalSeconds: number,
  options: FormatDurationSecondsOptions = {},
): string {
  const { style = "compact", suffix = "none", justNowBelowSec = 0 } = options;
  const sec = Math.max(0, Math.floor(totalSeconds));

  if (justNowBelowSec > 0 && sec < justNowBelowSec && suffix === "ago") {
    return "just now";
  }

  let core: string;
  if (style === "compact") {
    if (sec < SEC_MIN) {
      core = `${sec}s`;
    } else if (sec < SEC_HOUR) {
      core = `${Math.floor(sec / SEC_MIN)}m`;
    } else if (sec < SEC_DAY) {
      const hours = sec / SEC_HOUR;
      if (hours >= 10) {
        core = `${Math.round(hours)}h`;
      } else if (Number.isInteger(hours)) {
        core = `${hours}h`;
      } else {
        core = `${hours.toFixed(1)}h`;
      }
    } else {
      core = `${(sec / SEC_DAY).toFixed(1)}d`;
    }
  } else if (sec < SEC_MIN) {
    core = `${sec}s`;
  } else if (sec < SEC_HOUR) {
    const minutes = Math.floor(sec / SEC_MIN);
    const seconds = sec % SEC_MIN;
    core = seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  } else if (sec < SEC_DAY) {
    const hours = Math.floor(sec / SEC_HOUR);
    const minutes = Math.floor((sec % SEC_HOUR) / SEC_MIN);
    core = minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  } else {
    core = `${(sec / SEC_DAY).toFixed(1)}d`;
  }

  return withSuffix(core, suffix);
}

/** Relative time from seconds elapsed (e.g. API `seconds_ago` fields). */
export function formatTimeAgoSeconds(
  seconds: number | null | undefined,
  options: FormatDurationSecondsOptions & { nullLabel?: string } = {},
): string {
  const { nullLabel = "never", ...rest } = options;
  if (seconds == null) {
    return nullLabel;
  }
  return formatDurationSeconds(seconds, { ...rest, suffix: "ago" });
}

/** Relative time from an ISO timestamp. */
export function formatTimeAgoIso(
  iso: string | null | undefined,
  options: FormatDurationSecondsOptions & { nullLabel?: string; invalidLabel?: string } = {},
): string {
  const { nullLabel = "never", invalidLabel = "—", ...rest } = options;
  if (!iso?.trim()) {
    return nullLabel;
  }
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return invalidLabel;
  }
  const sec = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
  return formatDurationSeconds(sec, {
    ...rest,
    suffix: "ago",
    justNowBelowSec: rest.justNowBelowSec ?? 60,
  });
}

/** Relative time when the input is already in whole minutes. */
export function formatTimeAgoMinutes(minutes: number | null | undefined, nullLabel = "n/a"): string {
  if (minutes == null) {
    return nullLabel;
  }
  if (minutes <= 0) {
    return "just now";
  }
  return formatDurationSeconds(minutes * SEC_MIN, { suffix: "ago" });
}

/** Dev-hours card scaling (Command Center codebase atlas). */
export function formatHoursLikeCommandCenter(hours: number): string {
  if (hours >= 24) {
    return `${(hours / 24).toFixed(1)}d`;
  }
  return `${hours.toFixed(0)}h`;
}
