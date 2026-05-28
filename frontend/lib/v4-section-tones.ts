/** Shared section tone classes (platform matrix, settings accordion nav). */

export type V4SectionTone = "cyan" | "amber" | "pollen" | "magenta" | "green" | "purple" | "zinc" | "red";

const TONE_STYLES: Record<V4SectionTone, { section: string; header: string }> = {
  cyan: {
    section: "border-cyan/35 bg-cyan/[0.06] text-cyan",
    header: "text-cyan",
  },
  amber: {
    section: "border-pollen/35 bg-pollen/[0.06] text-pollen",
    header: "text-pollen",
  },
  pollen: {
    section: "border-pollen/35 bg-pollen/[0.06] text-pollen",
    header: "text-pollen",
  },
  magenta: {
    section: "border-[#FF00AA]/35 bg-[#FF00AA]/[0.06] text-[#FF00AA]",
    header: "text-[#FF00AA]",
  },
  green: {
    section: "border-[#00FF88]/35 bg-[#00FF88]/[0.06] text-[#00FF88]",
    header: "text-[#00FF88]",
  },
  purple: {
    section: "border-purple-400/35 bg-purple-400/[0.06] text-purple-300",
    header: "text-purple-300",
  },
  zinc: {
    section: "border-zinc-500/35 bg-zinc-500/[0.06] text-zinc-300",
    header: "text-zinc-300",
  },
  red: {
    section: "border-[#FF3366]/35 bg-[#FF3366]/[0.06] text-[#FF3366]",
    header: "text-[#FF3366]",
  },
};

/** Border/background shell for a toned section row. */
export function v4SectionToneShell(tone: V4SectionTone | string): string {
  return TONE_STYLES[tone as V4SectionTone]?.section ?? TONE_STYLES.zinc.section;
}

/** Title color for a toned section row. */
export function v4SectionToneHeader(tone: V4SectionTone | string): string {
  return TONE_STYLES[tone as V4SectionTone]?.header ?? TONE_STYLES.zinc.header;
}
