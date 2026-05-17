/**
 * Operator monitoring snapshot — mirrors ``GET /api/v1/operator/monitoring/snapshot``.
 */

export interface MonitoringHostMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_bytes: number;
  memory_total_bytes: number;
  swap_percent: number;
  swap_used_bytes: number;
  swap_total_bytes: number;
  disk_percent: number;
  disk_used_bytes: number;
  disk_total_bytes: number;
}

export interface MonitoringSnapshot {
  ts: string;
  collection_ms: number;
  host: MonitoringHostMetrics;
  docker: {
    running_containers: number | null;
    unavailable: boolean;
  };
  hive: {
    agents_active: number;
    agents_total: number;
    tasks_active: number;
    external_projects: number;
  };
  costs: {
    usd_24h: number;
    hourly_usd: { bucket: string; spend_usd: number }[];
  };
  critical_path: {
    supervisor_failures_24h: number;
    rate_limit_blocks_5m?: number;
    scaling_events_5m?: number;
  };
  enterprise?: {
    tenant_id: string | null;
    tier: string;
    usage: Record<string, number>;
    top_users_24h: Array<{
      subject: string;
      sessions: number;
      failures: number;
    }>;
    opentelemetry_ready: boolean;
    otlp_endpoint: boolean;
  };
  alerts: Array<{
    code: string;
    severity: "critical" | "warning" | "info";
    message: string;
  }>;
}
