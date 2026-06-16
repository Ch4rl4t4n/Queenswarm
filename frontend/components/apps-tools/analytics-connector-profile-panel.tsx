"use client";

import { ExternalLink, Loader2, Plug } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface ConnectorProfile {
  id: string;
  label: string;
  mode: string;
  ready: boolean;
  status: string;
  connector_slug: string | null;
  template_id: string | null;
  skill_slug: string;
  tools: string[];
  property_hint: string;
  configure_href: string;
  test_href: string | null;
  detail: string;
  last_tested_at: string | null;
  doc_url: string | null;
}

interface ConnectorProfileSnapshot {
  enabled: boolean;
  profiles: ConnectorProfile[];
  ready_count: number;
  operator_hint: string;
}

function statusTone(status: string): "ok" | "warn" | "info" | "purple" {
  if (status === "active") return "ok";
  if (status === "not_installed") return "warn";
  if (status === "needs_credentials") return "purple";
  return "info";
}

export function AnalyticsConnectorProfilePanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ConnectorProfileSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ConnectorProfileSnapshot>("analytics-workspace/connector-profile");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <V4Card data-testid="analytics-connector-profile-loading">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading connector profiles…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card id="analytics-connectors" data-testid="analytics-connector-profile">
      <V4CardHeader
        kicker="DA7 · Connector profile"
        title="Read-only data sources"
        description={snapshot.operator_hint}
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone="ok">{snapshot.ready_count} ready</V4Badge>
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
          </div>
        }
      />

      <div className="grid gap-3 px-4 pb-4 lg:grid-cols-2">
        {snapshot.profiles.map((profile) => (
          <article
            key={profile.id}
            className="rounded-lg border border-white/10 bg-black/25 p-4"
            data-testid={`analytics-connector-${profile.id}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-semibold text-(--qs-text)">
                  <Plug className="h-4 w-4 text-cyan" aria-hidden />
                  {profile.label}
                </h3>
                <p className="mt-1 text-xs text-(--qs-text-3)">{profile.detail}</p>
              </div>
              <V4Badge tone={statusTone(profile.status)}>{profile.status.replaceAll("_", " ")}</V4Badge>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <V4Badge tone="info">{profile.mode}</V4Badge>
              <V4Badge tone="gold">{profile.skill_slug}</V4Badge>
              {profile.property_hint ? (
                <V4Badge tone="purple">property {profile.property_hint}</V4Badge>
              ) : null}
            </div>

            {profile.tools.length > 0 ? (
              <p className="mt-2 font-mono text-xs text-(--qs-text-2)">
                Tools: {profile.tools.join(" · ")}
              </p>
            ) : null}

            <div className="mt-3 flex flex-wrap gap-2">
              <Link href={profile.configure_href} className="qs-btn qs-btn--primary qs-btn--sm">
                Configure
              </Link>
              {profile.doc_url ? (
                <a
                  href={profile.doc_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
                >
                  Docs
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </V4Card>
  );
}
