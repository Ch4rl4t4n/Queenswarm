import { describe, expect, it } from "vitest";

import { resolveAppsToolsAnalyticsCopy } from "@/lib/apps-tools-analytics-copy";

describe("resolveAppsToolsAnalyticsCopy", () => {
  it("returns language-specific copy when present", () => {
    const copy = resolveAppsToolsAnalyticsCopy("sk");
    expect(copy.usagePulseTitle).toBe("Pulz vyuzitia modulov");
    expect(copy.compactLabel).toBe("kompaktne");
  });

  it("falls back to english when requested language is missing", () => {
    const copy = resolveAppsToolsAnalyticsCopy("sk", {
      en: {
        usagePulseTitle: "English pulse",
        lastPrefix: "Last",
        eventsSuffix: "events",
        soloAnalyticsTag: "solo analytics",
        compactLabel: "compact",
        hintInteractionsTitle: "UX hint interactions",
        hintAvailabilityLabel: "availability",
        hintBetaLabel: "beta",
        hintTrendPrefix: "Hint trend",
        hintTrendQuiet: "quiet",
        hintTrendWatch: "watch",
        hintTrendHot: "hot",
        mcpSnapshotRetriesLabel: "MCP snapshot retries",
        mcpSnapshotLastRetryLabel: "last retry",
        mcpSnapshotRetryTrendLabel: "Retry trend",
        mcpRetryAnomalyBadge: "Retry anomaly",
        mcpSnapshotRetrySpikeRecommendation: "Retry spike detected in 24h — review MCP connector health and auth state.",
        mcpRetryAnomalyAcknowledgeCta: "Acknowledge anomaly",
        mcpRetryAnomalyClearCta: "Clear acknowledgment",
        mcpRetryAnomalyScopeWindowLabel: "this window",
        mcpRetryAnomalyScopeGlobalLabel: "global",
        mcpRetryAnomalyScopeChipLabel: "scope",
        mcpRetryLifecycleBadgePrefix: "Lifecycle",
        mcpRetryLifecycleActiveLabel: "active",
        mcpRetryLifecycleSuppressedLabel: "suppressed",
        mcpRetryLifecycleResurfacedLabel: "resurfaced",
        mcpRetryLifecycleRecommendationLabel: "MCP health-check signal",
        mcpRetryLifecycleRecommendationOpenCta: "Open MCP health checks",
        mcpRetryLifecycleRecommendationMonitorCta: "Monitor retry trend",
        mcpRetryLifecycleRecommendationLastOpenedLabel: "last opened",
        mcpRetryLifecycleRecommendationStripLabel: "Recommendation opens",
        mcpRetryLifecycleRecommendationCooldownLabel: "Retry in",
        mcpRetryLifecycleRecommendationOverrideCta: "Force open once",
        mcpRetryLifecycleRecommendationOverrideConfirmCta: "Confirm force open",
        mcpRetryLifecycleRecommendationOverrideStripLabel: "Force opens",
        mcpRetryAnomalyCardResetCta: "Reset anomaly ack",
        mcpRetryAnomalyAcknowledgedLabel: "Anomaly acknowledged",
        mcpRetryAnomalyAckedAgoLabel: "acked",
        mcpRetryAnomalyAckCountLabel: "anomaly acknowledgements",
        mcpRetryAnomalyRateSplitLabel: "Ack vs resurfaced",
        mcpRetryAnomalyActionHint:
          "Sustained retry anomaly detected. Validate MCP provider health checks before queue actions.",
        mcpRetryAnomalyActionCta: "Open MCP health checks",
        topMoversTitle: "Top movers",
        recommendationTitle: "Recommended next action",
      },
    });
    expect(copy.usagePulseTitle).toBe("English pulse");
  });
});
