import type { ReactNode, SVGProps } from "react";

type V4IconProps = SVGProps<SVGSVGElement> & { size?: number };

function V4Svg({ size = 16, children, ...props }: V4IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

/** Hive Control V4 — agents KPI icon. */
export function V4IconAgents(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </V4Svg>
  );
}

/** Hive Control V4 — running tasks / bolt. */
export function V4IconBolt(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </V4Svg>
  );
}

/** Hive Control V4 — queued tasks (variable-width lines). */
export function V4IconQueue(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="15" y2="12" />
      <line x1="3" y1="18" x2="18" y2="18" />
    </V4Svg>
  );
}

/** Hive Control V4 — tasks list icon. */
export function V4IconTasks(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </V4Svg>
  );
}

/** Hive Control V4 — LLM routing / CPU chip. */
export function V4IconCpu(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <rect x="9" y="9" width="6" height="6" />
      <line x1="9" y1="1" x2="9" y2="4" />
      <line x1="15" y1="1" x2="15" y2="4" />
      <line x1="9" y1="20" x2="9" y2="23" />
      <line x1="15" y1="20" x2="15" y2="23" />
      <line x1="20" y1="9" x2="23" y2="9" />
      <line x1="20" y1="14" x2="23" y2="14" />
      <line x1="1" y1="9" x2="4" y2="9" />
      <line x1="1" y1="14" x2="4" y2="14" />
    </V4Svg>
  );
}

/** Hive Control V4 — pollen / roster hub icon. */
export function V4IconPollen(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="3" r="2" />
      <circle cx="12" cy="21" r="2" />
      <circle cx="3" cy="12" r="2" />
      <circle cx="21" cy="12" r="2" />
      <circle cx="5.6" cy="5.6" r="1.5" />
      <circle cx="18.4" cy="18.4" r="1.5" />
      <circle cx="5.6" cy="18.4" r="1.5" />
      <circle cx="18.4" cy="5.6" r="1.5" />
    </V4Svg>
  );
}

/** Hive Control V4 — swarms / hex colony icon. */
export function V4IconSwarms(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <polygon points="12,2 22,7 22,17 12,22 2,17 2,7" />
      <line x1="2" y1="7" x2="12" y2="12" />
      <line x1="22" y1="7" x2="12" y2="12" />
      <line x1="12" y1="12" x2="12" y2="22" />
    </V4Svg>
  );
}

/** Hive Control V4 — foragers / compass spoke icon. */
export function V4IconForagers(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <path d="M12 2v6" />
      <path d="M12 22v-6" />
      <path d="m4.93 4.93 4.24 4.24" />
      <path d="m14.83 14.83 4.24 4.24" />
      <path d="M2 12h6" />
      <path d="M22 12h-6" />
      <path d="m4.93 19.07 4.24-4.24" />
      <path d="m14.83 9.17 4.24-4.24" />
    </V4Svg>
  );
}

/** Hive Control V4 — knowledge / HiveMind chunks. */
export function V4IconKnowledge(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <line x1="8" y1="7" x2="16" y2="7" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </V4Svg>
  );
}

/** Hive Control V4 — costs / coin. */
export function V4IconCoin(props: V4IconProps) {
  return (
    <V4Svg {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v12" />
      <path d="M16 9.5a3 3 0 0 0-3-2.5h-2a2.5 2.5 0 0 0 0 5h2a2.5 2.5 0 0 1 0 5h-2a3 3 0 0 1-3-2.5" />
    </V4Svg>
  );
}
