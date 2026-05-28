"use client";

import Link from "next/link";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import dynamic from "next/dynamic";
import { memo, useCallback, useEffect, useState } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface OnboardingStep {
  id: string;
  label: string;
  status: "done" | "ready" | "pending" | "blocked";
  detail: string;
  link: string | null;
}

interface PublishOnboardingSnapshot {
  generated_at: string;
  progress_pct: number;
  steps: OnboardingStep[];
  links: Record<string, string>;
  flags: Record<string, boolean>;
}

const PUBLISH_ONBOARDING_HINT = {
  title: { en: "Publish onboarding", sk: "Publish onboarding" },
  description: {
    en: "Checklist from Brain Pack to first live post. Default is simulate-only until SOCIAL_PUBLISH_LIVE_ENABLED=true.",
    sk: "Checklist od Brain Pack po prvý live post. Predvolene len simulate, kým nezapneš SOCIAL_PUBLISH_LIVE_ENABLED=true.",
  },
  options: {
    en: [
      "Load Brain Pack starter → bind My 3 Bees → run trio cycle.",
      "Marketing Ops → publish pack → Publish Queue approve.",
      "OAuth via Marketplace + Connector Hub (see OPERATOR_SOCIAL_OAUTH_SETUP.md).",
      "Social publish Simulate → enable live in .env.prod → redeploy → Live.",
    ],
    sk: [
      "Načítaj Brain Pack starter → bind My 3 Bees → spusti trio cycle.",
      "Marketing Ops → publish pack → schválenie v Publish Queue.",
      "OAuth cez Marketplace + Connector Hub (OPERATOR_SOCIAL_OAUTH_SETUP.md).",
      "Social Simulate → SOCIAL_PUBLISH_LIVE_ENABLED=true → redeploy → Live.",
    ],
  },
};

function stepIcon(status: OnboardingStep["status"]) {
  if (status === "done") {
    return <CheckCircle2 className="size-4 shrink-0 text-(--qs-green)" aria-hidden />;
  }
  return <Circle className="size-4 shrink-0 text-(--qs-muted)" aria-hidden />;
}

function OperatorPublishOnboardingPanelInner() {
  const [snapshot, setSnapshot] = useState<PublishOnboardingSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<PublishOnboardingSnapshot>("solo-operator/publish-onboarding");
      setSnapshot(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Onboarding snapshot unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading publish onboarding…
      </p>
    );
  }

  if (err || !snapshot) {
    return null;
  }

  if (snapshot.progress_pct >= 100) {
    return null;
  }

  return (
    <V4Card id="publish-onboarding">
      <V4CardHeader
        kicker="Publish lane"
        title="First live post — checklist"
        description={`${snapshot.progress_pct}% complete — simulate-first until OAuth + operator approve`}
        hint={
          <InfoHint
            title={PUBLISH_ONBOARDING_HINT.title}
            description={PUBLISH_ONBOARDING_HINT.description}
            options={PUBLISH_ONBOARDING_HINT.options}
            className="hive-inline-hint"
          />
        }
      />
      <div className="mb-4 h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-pollen transition-all duration-500"
          style={{ width: `${snapshot.progress_pct}%` }}
          role="progressbar"
          aria-valuenow={snapshot.progress_pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Publish onboarding progress"
        />
      </div>
      <ol className="space-y-2">
        {snapshot.steps.map((step) => (
          <li
            key={step.id}
            className={cn(
              "flex gap-3 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2.5 text-sm",
              step.status === "done" && "border-(--qs-green)/25 opacity-80",
            )}
          >
            {stepIcon(step.status)}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-(--qs-text)">{step.label}</span>
                <V4Badge tone={step.status === "done" ? "ok" : step.status === "ready" ? "gold" : "info"}>
                  {step.status}
                </V4Badge>
              </div>
              <p className="mt-0.5 text-xs text-(--qs-muted)">{step.detail}</p>
              {step.link && step.status !== "done" ? (
                <Link href={step.link} className="mt-1 inline-block text-xs text-(--qs-cyan) underline-offset-2 hover:underline">
                  Open →
                </Link>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-(--qs-muted)">
        Full guide:{" "}
        <span className="font-mono text-(--qs-text-3)">docs/OPERATOR_PUBLISH_LANE_MANUAL.md</span>
        {" · "}
        <span className="font-mono text-(--qs-text-3)">docs/OPERATOR_FIRST_LIVE_POST.md</span>
        {" · "}
        <Link href={snapshot.links.execution_studio ?? "/integrations?tab=studio"} className="text-(--qs-cyan) underline-offset-2 hover:underline">
          Execution Studio
        </Link>
      </p>
    </V4Card>
  );
}

export const OperatorPublishOnboardingPanel = memo(OperatorPublishOnboardingPanelInner);
OperatorPublishOnboardingPanel.displayName = "OperatorPublishOnboardingPanel";

const LazyOperatorPublishOnboardingPanel = dynamic(
  () => Promise.resolve({ default: OperatorPublishOnboardingPanel }),
  { ssr: false, loading: () => null },
);

export { LazyOperatorPublishOnboardingPanel };
