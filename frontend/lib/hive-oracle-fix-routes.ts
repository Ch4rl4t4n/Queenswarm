/** Hive Oracle warning Fix CTA — labels and href normalization for deep links. */

import { executionStudioSectionHref } from "@/lib/integrations-routes";

export interface OracleFixCta {
  label: string;
  hint: string;
}

const ORACLE_FIX_CTA: Record<string, OracleFixCta> = {
  publish_backlog: {
    label: "Review queue",
    hint: "Open Publish Queue — approve or reject pending packs before live publish.",
  },
  overnight_stalled: {
    label: "Check overnight",
    hint: "Open Operator Loop — triage stalled signals from Dump & Sleep.",
  },
  publish_onboarding_gap: {
    label: "Complete setup",
    hint: "Open Operator Hub — finish OAuth and simulate steps for the publish lane.",
  },
  trio_unbound: {
    label: "Bind bees",
    hint: "Open Operator Hub — bind My 3 Bees lanes for the morning cycle.",
  },
  immune_quarantine: {
    label: "Review fleet",
    hint: "Open Swarm Fleet — resume or adjust quarantined autopilot routines.",
  },
  immune_watch: {
    label: "Review fleet",
    hint: "Open Swarm Fleet — inspect routines on immune watch.",
  },
  trading_halted: {
    label: "Trading cockpit",
    hint: "Review halt reason and risk limits in Trading Cockpit.",
  },
  innovation_pending: {
    label: "Review proposals",
    hint: "Open Innovation Lab — approve or reject pending proposals.",
  },
  fleet_paused: {
    label: "Resume fleet",
    hint: "Open Swarm Fleet — re-enable paused autopilot routines.",
  },
};

/** Contextual Fix button label for a warning id. */
export function oracleFixLabel(warningId: string): string {
  return ORACLE_FIX_CTA[warningId]?.label ?? "Open fix";
}

/** Tooltip / aria description for Fix CTA. */
export function oracleFixHint(warningId: string): string {
  return ORACLE_FIX_CTA[warningId]?.hint ?? "Navigate to the recommended operator surface to resolve this warning.";
}

/** Upgrade legacy studio hashes to include workspace section query param. */
export function normalizeOracleFixHref(href: string): string {
  if (!href.includes("/integrations?tab=studio")) {
    return href;
  }
  if (href.includes("section=")) {
    return href;
  }
  const hashIdx = href.indexOf("#");
  const hash = hashIdx === -1 ? "" : href.slice(hashIdx);
  const workspace =
    hash.includes("publish-queue")
    || hash.includes("social-publish")
    || hash.includes("publish-performance")
    || hash.includes("trading")
      ? "publish"
      : hash.includes("live-lane") || hash.includes("media-agency") || hash.includes("micro-saas")
        ? "lanes"
        : hash.includes("innovation-lab")
          ? "innovation"
          : null;
  if (!workspace) {
    return href;
  }
  const scrollTarget = hash.replace(/^#/, "") || undefined;
  return executionStudioSectionHref(workspace, scrollTarget);
}
