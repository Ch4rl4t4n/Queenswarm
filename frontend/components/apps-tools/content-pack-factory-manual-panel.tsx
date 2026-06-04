"use client";

import Link from "next/link";
import { CheckCircle2Icon } from "lucide-react";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import {
  CONTENT_PACK_FACTORY_MANUAL_DOC,
  CONTENT_PACK_FACTORY_PREREQUISITES,
  CONTENT_PACK_FACTORY_RECOMMENDATIONS,
  CONTENT_PACK_FACTORY_STEPS,
  FACTORY_FIRST_REVENUE_MANUAL_DOC,
} from "@/lib/content-pack-factory-manual";

/** In-app operator guide for Content Pack Factory (Pack factory tab). */
export function ContentPackFactoryManualPanel(): JSX.Element {
  return (
    <div className="space-y-4">
      <V4Card id="content-pack-prerequisites">
        <V4CardHeader
          kicker="Before you start"
          title="One-time setup"
          description="Content Pack Factory needs working LLM keys — builds fail quality gate without OpenAI or funded Anthropic."
          hint={
            <InfoHint
              title="Prerequisites"
              description="Same LLM vault as Skill Factory. Run smoke test on server before first Build."
              options={[
                "OpenAI gpt-4o-mini — recommended minimum",
                "Auto-approve ON for solo",
                "Gumroad optional — manual upload from LISTING.md works",
              ]}
              manualHref="/manual#content-pack-factory"
            />
          }
        />
        <ul className="mt-3 space-y-2">
          {CONTENT_PACK_FACTORY_PREREQUISITES.map((row) => (
            <li key={row.id} className="flex gap-2 text-sm text-(--qs-text-2)">
              <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
              <span>
                <strong className="text-(--qs-text)">{row.label}</strong>
                {" — "}
                {row.detail}
                {row.href ? (
                  <>
                    {" "}
                    <Link href={row.href} className="text-cyan underline">
                      Open →
                    </Link>
                  </>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      </V4Card>

      <V4Card id="content-pack-pipeline">
        <V4CardHeader
          kicker="Production pipeline"
          title="Research → build → forge → export"
          description="Five steps with hints. Approve verified_content_pack_forge before Library fills."
        />
        <ol className="mt-3 space-y-4">
          {CONTENT_PACK_FACTORY_STEPS.map((step) => (
            <li key={step.id} className="qs-bubble p-3 text-sm">
              <p className="font-semibold text-(--qs-text)">{step.title}</p>
              <p className="mt-1 text-(--qs-text-2)">{step.summary}</p>
              <p className="mt-2 text-xs text-pollen">
                <strong>Hint:</strong> {step.hint}
              </p>
              <ul className="mt-2 list-inside list-disc text-xs text-(--qs-text-3)">
                {step.actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
              {step.link ? (
                <Link href={step.link.href} className="mt-2 inline-block text-xs text-cyan underline">
                  {step.link.label} →
                </Link>
              ) : null}
            </li>
          ))}
        </ol>
      </V4Card>

      <V4Card id="content-pack-recommendations">
        <V4CardHeader title="Recommendations" description="Operator best practices for pack factory revenue." />
        <ul className="mt-2 space-y-2 text-sm text-(--qs-text-2)">
          {CONTENT_PACK_FACTORY_RECOMMENDATIONS.map((row) => (
            <li key={row.id}>
              <strong className="text-(--qs-text)">{row.title}</strong> — {row.body}
            </li>
          ))}
        </ul>
      </V4Card>

      <V4Card id="content-pack-server-scripts">
        <V4CardHeader
          title="Server operator scripts"
          description="Run inside backend container or via factory-first-revenue-bootstrap.sh"
          hint={
            <InfoHint
              title="Bootstrap"
              description="One command runs seed, research, export refresh, LLM smoke, and cycle status."
              options={["./scripts/factory-first-revenue-bootstrap.sh", FACTORY_FIRST_REVENUE_MANUAL_DOC]}
            />
          }
        />
        <ul className="mt-2 space-y-1 font-mono text-xs text-(--qs-text-3)">
          <li>factory_llm_readiness.py --smoke</li>
          <li>factory_abort_llm_blocked_builds.py</li>
          <li>factory_reset_failed_opportunities.py --apply</li>
          <li>content_pack_factory_cycle_status.py</li>
        </ul>
        <p className="mt-3 text-xs text-(--qs-text-3)">
          Full manual: <code className="text-pollen">{CONTENT_PACK_FACTORY_MANUAL_DOC}</code>
        </p>
      </V4Card>
    </div>
  );
}
