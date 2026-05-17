import { HivePageHeader } from "@/components/hive/hive-page-header";
import { InfoHint } from "@/components/hive/info-hint";
import { APP_FUNCTION_GUIDE, APP_MANUAL_SECTIONS } from "@/lib/manual-content";

export const dynamic = "force-dynamic";

export default function ManualPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Manual"
        subtitle="Kompletný návod na presné používanie celej aplikácie Queenswarm vrátane funkcií a možností nastavenia."
      />

      <section className="space-y-5 rounded-3xl border border-cyan/20 bg-[#070d17]/70 p-5 md:p-7">
        {APP_MANUAL_SECTIONS.map((section) => (
          <article key={section.id} className="space-y-3 border-b border-zinc-800/80 pb-5 last:border-b-0 last:pb-0">
            <h2 className="text-lg font-semibold text-zinc-100">{section.title}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} className="text-sm leading-relaxed text-zinc-300">
                {paragraph}
              </p>
            ))}
            {section.checklist?.length ? (
              <ol className="list-decimal space-y-1 pl-5 text-sm text-zinc-300">
                {section.checklist.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            ) : null}
          </article>
        ))}
      </section>

      <section className="space-y-4 rounded-3xl border border-[#FFB800]/30 bg-[#100d07]/50 p-5 md:p-7">
        <header className="space-y-1">
          <h2 className="text-lg font-semibold text-zinc-100">Funkcie aplikácie a info popisy</h2>
          <p className="text-sm text-zinc-300">
            Každá funkcia nižšie má `Info` ikonu s popisom funkcionality a možností nastavenia.
          </p>
        </header>

        <div className="space-y-5">
          {APP_FUNCTION_GUIDE.map((group) => (
            <article key={group.id} className="space-y-3 rounded-2xl border border-zinc-800/80 bg-black/25 p-4">
              <h3 className="text-base font-semibold text-zinc-100">{group.title}</h3>
              <div className="grid gap-2 md:grid-cols-2">
                {group.items.map((item) => (
                  <div key={item.id} className="flex items-start justify-between gap-3 rounded-xl border border-zinc-800 bg-[#060b12] p-3">
                    <div>
                      <p className="text-sm font-medium text-zinc-100">{item.label}</p>
                      <p className="mt-1 text-xs text-zinc-400">{item.description}</p>
                    </div>
                    <InfoHint title={item.label} description={item.description} options={item.options} />
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

