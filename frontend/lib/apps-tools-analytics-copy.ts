import type { UiLanguage } from "@/lib/ui-language";

export interface AppsToolsAnalyticsCopy {
  usagePulseTitle: string;
  lastPrefix: string;
  eventsSuffix: string;
  soloAnalyticsTag: string;
  compactLabel: string;
  hintInteractionsTitle: string;
  hintAvailabilityLabel: string;
  hintBetaLabel: string;
  hintTrendPrefix: string;
  hintTrendQuiet: string;
  hintTrendWatch: string;
  hintTrendHot: string;
  mcpSnapshotRetriesLabel: string;
  mcpSnapshotLastRetryLabel: string;
  mcpSnapshotRetryTrendLabel: string;
  mcpRetryAnomalyBadge: string;
  mcpSnapshotRetrySpikeRecommendation: string;
  mcpRetryAnomalyAcknowledgeCta: string;
  mcpRetryAnomalyClearCta: string;
  mcpRetryAnomalyScopeWindowLabel: string;
  mcpRetryAnomalyScopeGlobalLabel: string;
  mcpRetryAnomalyScopeChipLabel: string;
  mcpRetryLifecycleBadgePrefix: string;
  mcpRetryLifecycleActiveLabel: string;
  mcpRetryLifecycleSuppressedLabel: string;
  mcpRetryLifecycleResurfacedLabel: string;
  mcpRetryLifecycleRecommendationLabel: string;
  mcpRetryLifecycleRecommendationOpenCta: string;
  mcpRetryLifecycleRecommendationMonitorCta: string;
  mcpRetryLifecycleRecommendationLastOpenedLabel: string;
  mcpRetryLifecycleRecommendationStripLabel: string;
  mcpRetryLifecycleRecommendationCooldownLabel: string;
  mcpRetryLifecycleRecommendationOverrideCta: string;
  mcpRetryLifecycleRecommendationOverrideConfirmCta: string;
  mcpRetryLifecycleRecommendationOverrideStripLabel: string;
  mcpRetryAnomalyCardResetCta: string;
  mcpRetryAnomalyAcknowledgedLabel: string;
  mcpRetryAnomalyAckedAgoLabel: string;
  mcpRetryAnomalyAckCountLabel: string;
  mcpRetryAnomalyRateSplitLabel: string;
  mcpRetryAnomalyActionHint: string;
  mcpRetryAnomalyActionCta: string;
  topMoversTitle: string;
  recommendationTitle: string;
}

const DEFAULT_ANALYTICS_COPY_EN: AppsToolsAnalyticsCopy = {
  usagePulseTitle: "Module usage pulse",
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
  mcpRetryAnomalyActionHint: "Sustained retry anomaly detected. Validate MCP provider health checks before queue actions.",
  mcpRetryAnomalyActionCta: "Open MCP health checks",
  topMoversTitle: "Top movers",
  recommendationTitle: "Recommended next action",
};

export const APPS_TOOLS_ANALYTICS_COPY: Partial<Record<UiLanguage, AppsToolsAnalyticsCopy>> = {
  en: DEFAULT_ANALYTICS_COPY_EN,
  sk: {
    usagePulseTitle: "Pulz vyuzitia modulov",
    lastPrefix: "Naposledy",
    eventsSuffix: "udalosti",
    soloAnalyticsTag: "solo analytika",
    compactLabel: "kompaktne",
    hintInteractionsTitle: "UX interakcie hintov",
    hintAvailabilityLabel: "dostupnost",
    hintBetaLabel: "beta",
    hintTrendPrefix: "Trend hintov",
    hintTrendQuiet: "kludne",
    hintTrendWatch: "sledovat",
    hintTrendHot: "horuce",
    mcpSnapshotRetriesLabel: "MCP snapshot retry",
    mcpSnapshotLastRetryLabel: "posledny retry",
    mcpSnapshotRetryTrendLabel: "Trend retry",
    mcpRetryAnomalyBadge: "Retry anomalia",
    mcpSnapshotRetrySpikeRecommendation: "Spicka retry v 24h — skontroluj health a auth stav MCP konektorov.",
    mcpRetryAnomalyAcknowledgeCta: "Potvrdit anomaliu",
    mcpRetryAnomalyClearCta: "Zrusit potvrdenie",
    mcpRetryAnomalyScopeWindowLabel: "toto okno",
    mcpRetryAnomalyScopeGlobalLabel: "globalne",
    mcpRetryAnomalyScopeChipLabel: "scope",
    mcpRetryLifecycleBadgePrefix: "Lifecycle",
    mcpRetryLifecycleActiveLabel: "aktivna",
    mcpRetryLifecycleSuppressedLabel: "potlacena",
    mcpRetryLifecycleResurfacedLabel: "znovuobjavena",
    mcpRetryLifecycleRecommendationLabel: "MCP health-check signal",
    mcpRetryLifecycleRecommendationOpenCta: "Otvorit MCP health checks",
    mcpRetryLifecycleRecommendationMonitorCta: "Sledovat trend retry",
    mcpRetryLifecycleRecommendationLastOpenedLabel: "naposledy otvorene",
    mcpRetryLifecycleRecommendationStripLabel: "Otvorenia odporucania",
    mcpRetryLifecycleRecommendationCooldownLabel: "Skusit znova za",
    mcpRetryLifecycleRecommendationOverrideCta: "Vynutit otvorenie raz",
    mcpRetryLifecycleRecommendationOverrideConfirmCta: "Potvrdit vynutene otvorenie",
    mcpRetryLifecycleRecommendationOverrideStripLabel: "Vynutene otvorenia",
    mcpRetryAnomalyCardResetCta: "Reset potvrdenia anomalie",
    mcpRetryAnomalyAcknowledgedLabel: "Anomalia potvrdena",
    mcpRetryAnomalyAckedAgoLabel: "potvrdene",
    mcpRetryAnomalyAckCountLabel: "potvrdenia anomalie",
    mcpRetryAnomalyRateSplitLabel: "Potvrdene vs znovuobjavene",
    mcpRetryAnomalyActionHint: "Trvala retry anomalia. Pred queue akciami over health MCP providerov.",
    mcpRetryAnomalyActionCta: "Otvorit MCP health checks",
    topMoversTitle: "Najvacsie pohyby",
    recommendationTitle: "Odporucany dalsi krok",
  },
};

export function resolveAppsToolsAnalyticsCopy(
  language: UiLanguage,
  source: Partial<Record<UiLanguage, AppsToolsAnalyticsCopy>> = APPS_TOOLS_ANALYTICS_COPY,
): AppsToolsAnalyticsCopy {
  return source[language] ?? source.en ?? DEFAULT_ANALYTICS_COPY_EN;
}
