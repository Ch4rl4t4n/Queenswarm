/** Stagger first dashboard poll so mount does not burst past rate limits. */

export const DASHBOARD_BOOT_STAGGER_MS = {
  shellSummary: 0,
  shellTenants: 500,
  platformMe: 300,
  colonySummary: 800,
  colonyCosts: 1200,
  colonyTelemetry: 1800,
  paperTrading: 2400,
  swarmBoard: 3200,
  taskQueue: 4000,
  workflows: 4800,
  agentSuggestions: 5600,
  rapidLoop: 6000,
  dreamingSummary: 6400,
  timeSaved: 6800,
} as const;
