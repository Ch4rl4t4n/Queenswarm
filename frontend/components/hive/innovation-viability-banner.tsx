"use client";

import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { memo } from "react";

import { V4Badge } from "@/components/ui/v4";

export interface ViabilityCheck {
  id: string;
  label: string;
  status: "pass" | "warn" | "block";
  detail: string;
}

export interface ViabilityPayload {
  ok: boolean;
  status: "pass" | "warn" | "block";
  checks: ViabilityCheck[];
  blocked_reasons: string[];
}

interface InnovationViabilityBannerProps {
  viability: ViabilityPayload | null;
  loading?: boolean;
}

function statusIcon(status: ViabilityCheck["status"]): JSX.Element {
  if (status === "pass") {
    return <CheckCircle2 className="size-3.5 text-(--qs-green)" aria-hidden />;
  }
  if (status === "warn") {
    return <AlertTriangle className="size-3.5 text-pollen" aria-hidden />;
  }
  return <XCircle className="size-3.5 text-(--qs-red)" aria-hidden />;
}

/** Inline viability gate results before Innovation Lab → Maintainer handoff. */
function InnovationViabilityBannerInner({ viability, loading }: InnovationViabilityBannerProps): JSX.Element | null {
  if (loading) {
    return (
      <p className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        Checking viability gate…
      </p>
    );
  }
  if (!viability) {
    return null;
  }

  return (
    <div
      className="mt-3 rounded-lg border border-(--qs-border)/50 bg-black/25 p-3"
      data-testid="innovation-viability-banner"
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-(--qs-text)">Viability gate</span>
        <V4Badge tone={viability.ok ? "ok" : "warn"}>{viability.status}</V4Badge>
      </div>
      <ul className="space-y-1">
        {viability.checks.map((check) => (
          <li key={check.id} className="flex items-start gap-2 text-[11px] text-(--qs-text-2)">
            {statusIcon(check.status)}
            <span>
              <strong>{check.label}:</strong> {check.detail}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export const InnovationViabilityBanner = memo(InnovationViabilityBannerInner);
