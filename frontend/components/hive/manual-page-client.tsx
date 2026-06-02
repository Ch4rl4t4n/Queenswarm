"use client";

import Link from "next/link";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { InfoHint } from "@/components/hive/info-hint";
import { ManualOpenLink, ManualRichText } from "@/components/hive/manual-rich-text";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import {
  functionGuideGroups,
  functionGuideHeading,
  functionGuideIntro,
  manualSections,
  manualSubtitle,
} from "@/lib/manual-i18n";
import type { ManualChecklistItem } from "@/lib/manual-content";

/** Manual — function names in English; prose follows Settings language toggle. */
export function ManualPageClient(): JSX.Element {
  const { language } = useUiLanguage();
  const sections = manualSections(language);
  const guide = functionGuideGroups(language);

  return (
    <HivePageShell
      title="Manual"
      subtitle={manualSubtitle(language)}
      hintKey="manual"
      canvasClassName="gap-8"
    >
      <section className="manual-section space-y-5 rounded-3xl border border-cyan/20 bg-[#070d17]/70 p-4 md:p-7">
        {sections.map((section) => (
          <article key={section.id} id={section.id} className="space-y-3 border-b border-zinc-800/80 pb-5 last:border-b-0 last:pb-0 scroll-mt-24">
            <h2 className="text-lg font-semibold text-zinc-100">{section.title}</h2>
            {section.paragraphs.map((paragraph: string) => (
              <p key={paragraph} className="text-sm leading-relaxed text-zinc-300">
                <ManualRichText text={paragraph} />
              </p>
            ))}
            {section.checklist?.length ? (
              <ol className="list-decimal space-y-2 pl-5 text-sm text-zinc-300">
                {section.checklist.map((item: ManualChecklistItem) => (
                  <li key={`${section.id}-${item.text}`} className="leading-relaxed">
                    <ManualRichText text={item.text} />
                    {item.href ? (
                      <ManualOpenLink href={item.href} label={item.linkLabel ?? "Open"} />
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : null}
          </article>
        ))}
      </section>

      <section className="manual-section space-y-4 rounded-3xl border border-[#FFB800]/30 bg-[#100d07]/50 p-4 md:p-7">
        <header className="space-y-1">
          <h2 className="text-lg font-semibold text-zinc-100">{functionGuideHeading(language)}</h2>
          <p className="text-sm text-zinc-300">{functionGuideIntro(language)}</p>
        </header>

        <div className="space-y-5">
          {guide.map((group) => (
            <article key={group.id} className="space-y-3 rounded-2xl border border-zinc-800/80 bg-black/25 p-4">
              <h3 className="text-base font-semibold text-zinc-100">{group.title}</h3>
              <div className="grid gap-2 md:grid-cols-2">
                {group.items.map((item) => (
                  <div
                    key={item.id}
                    className="manual-func-item flex flex-col gap-3 rounded-xl border border-zinc-800 bg-[#060b12] p-3 sm:flex-row sm:items-start sm:justify-between"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-zinc-100">{item.label}</p>
                      <p className="mt-1 text-xs leading-relaxed text-zinc-400">{item.description}</p>
                      {item.href ? (
                        <Link
                          href={item.href}
                          className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-cyan hover:text-pollen"
                        >
                          Open in app
                          <span aria-hidden>→</span>
                        </Link>
                      ) : null}
                    </div>
                    <InfoHint
                      title={item.label}
                      description={item.description}
                      options={item.options}
                      manualHref={item.href}
                    />
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </HivePageShell>
  );
}
