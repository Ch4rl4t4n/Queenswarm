"use client";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import type { HarnessSnapshotPayload } from "@/lib/hive-types";

interface QueenMaintainerWebhookPanelProps {
  snapshot: HarnessSnapshotPayload;
}

/** Post-merge GitHub webhook status for Queen Maintainer (operator setup guide). */
export function QueenMaintainerWebhookPanel({ snapshot }: QueenMaintainerWebhookPanelProps): JSX.Element | null {
  const maintainer = snapshot.queen_maintainer;
  if (!maintainer) {
    return null;
  }

  const webhook = maintainer.post_merge_webhook;

  return (
    <V4Card>
      <V4CardHeader
        kicker="Queen Maintainer"
        title="Post-merge GitHub trigger"
        description="After merge to main/master, spawn a PR-only Maintainer supervisor session (HMAC verified)."
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <V4Badge tone={maintainer.enabled ? "ok" : "warn"}>
          Maintainer {maintainer.enabled ? "on" : "off"}
        </V4Badge>
        <V4Badge tone={webhook.enabled ? "ok" : "info"}>
          Webhook {webhook.enabled ? "enabled" : "disabled"}
        </V4Badge>
        <V4Badge tone={webhook.secret_configured ? "ok" : "warn"}>
          Secret {webhook.secret_configured ? "set" : "missing"}
        </V4Badge>
        <V4Badge tone={webhook.tenant_id_configured ? "ok" : "warn"}>
          Tenant {webhook.tenant_id_configured ? "set" : "missing"}
        </V4Badge>
      </div>
      <ul className="mt-4 space-y-2 text-sm text-(--qs-text-2)">
        <li>
          Webhook URL:{" "}
          <span className="font-mono text-xs text-cyan">
            https://queenswarm.love{webhook.webhook_path}
          </span>
        </li>
        <li>
          Events:{" "}
          <span className="font-mono text-xs text-(--qs-muted)">{webhook.accepted_events.join(", ")}</span>
        </li>
        {webhook.github_owner && webhook.github_repo ? (
          <li>
            Repo filter:{" "}
            <span className="font-mono text-xs text-pollen">
              {webhook.github_owner}/{webhook.github_repo}
            </span>
          </li>
        ) : null}
      </ul>
      <p className="mt-3 text-xs text-(--qs-muted)">
        Env: <span className="font-mono">QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=true</span>,{" "}
        <span className="font-mono">QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET</span>,{" "}
        <span className="font-mono">QUEEN_MAINTAINER_POST_MERGE_TENANT_ID</span>
      </p>
    </V4Card>
  );
}
