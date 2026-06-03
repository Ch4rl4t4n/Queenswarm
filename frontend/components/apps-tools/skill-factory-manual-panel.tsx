"use client";

import Link from "next/link";
import { BookOpenIcon, CheckCircle2Icon, CircleIcon, ExternalLinkIcon } from "lucide-react";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import {
  SKILL_FACTORY_GAPS,
  SKILL_FACTORY_PREREQUISITES,
  SKILL_FACTORY_RECOMMENDATIONS,
  SKILL_FACTORY_STEPS,
} from "@/lib/skill-factory-manual";
import { cn } from "@/lib/utils";

function gapTone(status: "done" | "operator" | "planned"): "ok" | "info" | "warn" {
  if (status === "done") return "ok";
  if (status === "operator") return "warn";
  return "info";
}

function gapLabel(status: "done" | "operator" | "planned"): string {
  if (status === "done") return "hotové";
  if (status === "operator") return "tvoj krok";
  return "plánované";
}

/** Full operator guide — prerequisites, step-by-step pipeline, recommendations, gaps. */
export function SkillFactoryManualPanel(): JSX.Element {
  return (
    <div className="mt-4 space-y-4">
      <V4Card id="skill-factory-prerequisites">
        <V4CardHeader
          kicker="Pred začatím"
          title="Jednorazová príprava"
          description="Skontroluj pred prvým Build skill — bez LLM keys factory session zlyhá."
          hint={
            <InfoHint
              title="Prerequisites"
              description="Skill Factory je výrobná linka, nie chat. Potrebuje LLM, Celery a verify loop."
              options={[
                "LLM keys — Grok/Claude minimum",
                "Auto-approve ON pre solo",
                "HiveMind — voliteľné, zlepšuje research",
              ]}
              manualHref="/manual#skill-factory"
            />
          }
        />
        <ul className="mt-3 space-y-2">
          {SKILL_FACTORY_PREREQUISITES.map((row) => (
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
                      Otvoriť →
                    </Link>
                  </>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      </V4Card>

      <V4Card id="skill-factory-pipeline">
        <V4CardHeader
          kicker="Proces výroby"
          title="Od nuly po GitHub pack"
          description="8 krokov — každý s hintom. Primary path: Research → Build → Approve → Export → Use."
          hint={
            <InfoHint
              title="Factory pipeline"
              description="~85 % automatizované. Ty schvaľuješ forge a pushneš export mimo apky."
              options={[
                "Simulate-first — critic pred operátorom",
                "Tenant registry — agenti vidia skill hneď po approve",
                "Full manual: docs/SKILL_FACTORY_OPERATOR_MANUAL.md",
              ]}
              manualHref="/manual#skill-factory"
            />
          }
        />
        <ol className="mt-4 space-y-4">
          {SKILL_FACTORY_STEPS.map((step) => (
            <li
              key={step.id}
              className={cn(
                "rounded-xl border px-4 py-3",
                step.optional ? "border-white/10 bg-black/20" : "border-pollen/20 bg-pollen/5",
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="font-semibold text-(--qs-text)">
                  {step.title}
                  {step.optional ? (
                    <V4Badge tone="info" className="ml-2 inline text-[10px]">
                      voliteľné
                    </V4Badge>
                  ) : null}
                </p>
                <InfoHint
                  title={step.title}
                  description={step.hint}
                  options={step.actions.slice(0, 4)}
                  manualHref="/manual#skill-factory"
                />
              </div>
              <p className="mt-1 text-sm text-(--qs-text-3)">{step.summary}</p>
              <ul className="mt-2 space-y-1">
                {step.actions.map((action) => (
                  <li key={action} className="flex gap-2 text-xs text-(--qs-text-3)">
                    <CircleIcon className="mt-0.5 size-3 shrink-0 text-pollen" aria-hidden />
                    {action}
                  </li>
                ))}
              </ul>
              {step.link ? (
                <Link href={step.link.href} className="mt-2 inline-flex items-center gap-1 text-xs text-cyan underline">
                  {step.link.label}
                  <ExternalLinkIcon className="size-3" aria-hidden />
                </Link>
              ) : null}
            </li>
          ))}
        </ol>
      </V4Card>

      <V4Card id="skill-factory-recommendations">
        <V4CardHeader title="Odporúčania stratégie" description="Biznis + technické — čo robiť a čomu sa vyhnúť." />
        <ul className="mt-3 space-y-3">
          {SKILL_FACTORY_RECOMMENDATIONS.map((row) => (
            <li key={row.id} className="rounded-lg border border-white/10 bg-black/25 px-3 py-2">
              <p className="text-sm font-medium text-pollen">{row.title}</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">{row.body}</p>
            </li>
          ))}
        </ul>
      </V4Card>

      <V4Card id="skill-factory-gaps">
        <V4CardHeader
          title="Stav systému — čo ešte treba"
          description="Transparentný checklist funkcionality vs. tvoja operátorská práca."
        />
        <ul className="mt-3 space-y-2">
          {SKILL_FACTORY_GAPS.map((row) => (
            <li key={row.id} className="flex flex-wrap items-start gap-2 text-sm">
              <V4Badge tone={gapTone(row.status)}>{gapLabel(row.status)}</V4Badge>
              <span className="font-medium text-(--qs-text)">{row.label}</span>
              <span className="w-full text-xs text-(--qs-text-3)">{row.detail}</span>
            </li>
          ))}
        </ul>
      </V4Card>

      <p className="flex items-center gap-2 text-xs text-(--qs-text-4)">
        <BookOpenIcon className="size-3.5" aria-hidden />
        Rozšírená verzia:{" "}
        <Link href="/manual#skill-factory" className="text-cyan underline">
          Operator Manual → Skill Factory
        </Link>
      </p>
    </div>
  );
}
