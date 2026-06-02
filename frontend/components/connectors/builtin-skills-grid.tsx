"use client";

import Link from "next/link";
import { BookOpenIcon } from "lucide-react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Chip } from "@/components/ui/v4";
import type { SkillCatalogBuiltinItem } from "@/lib/hive-types";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";

export interface BuiltinSkillsGridProps {
  skills: SkillCatalogBuiltinItem[];
  loading?: boolean;
}

function primaryRoleLabel(roles: string[]): string {
  if (!roles.length) return "supervisor";
  return roles[0]!.replaceAll("_", " ");
}

function builtinAgentUsage(skill: SkillCatalogBuiltinItem): string {
  if (skill.agent_usage?.trim()) return skill.agent_usage.trim();
  const roles = (skill.roles ?? []).length ? (skill.roles ?? []).join(", ") : "supervisor";
  const keywords = (skill.keywords ?? []).slice(0, 5).join(", ");
  return keywords
    ? `Queen and ${roles} bees inject this shard when tasks match: ${keywords}.`
    : `Supervisor SkillLibrary loads ${skill.slug} for ${roles} during planning and execution.`;
}

function builtinSummary(skill: SkillCatalogBuiltinItem): string {
  if (skill.summary?.trim()) return skill.summary.trim();
  return `Built-in markdown skill for ${primaryRoleLabel(skill.roles ?? [])} lanes.`;
}

/** Built-in hive skills — marketplace-style cards with safe tag wrapping. */
export function BuiltinSkillsGrid({ skills, loading = false }: BuiltinSkillsGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(skills, pageSize, `${pageSize}|${skills.length}|${loading}`);

  if (loading) {
    return (
      <div className="builtin-skills-grid-wrap mt-4 min-w-0 space-y-3">
        <div className="hub-catalog-section-head flex flex-wrap items-center gap-2">
          <p className="hub-catalog-section-head__label">ALL SKILLS</p>
          <V4Badge tone="info">loading…</V4Badge>
        </div>
        <div className="hub-catalog-grid">
          {Array.from({ length: 4 }, (_, index) => (
            <article
              key={`skill-skel-${index}`}
              className="v4-dream-cycle-card animate-pulse"
              aria-hidden
            >
              <div className="h-4 w-40 rounded bg-white/15" />
              <div className="mt-3 h-3 w-full rounded bg-white/10" />
              <div className="mt-2 h-16 w-full rounded bg-white/10" />
            </article>
          ))}
        </div>
      </div>
    );
  }

  if (!skills.length) {
    return (
      <p className="mt-4 text-sm text-(--qs-text-3)">No built-in hive skills found in SkillLibrary.</p>
    );
  }

  return (
    <div className="builtin-skills-grid-wrap mt-4 min-w-0 space-y-3">
      <div className="hub-catalog-section-head flex flex-wrap items-center gap-2">
        <p className="hub-catalog-section-head__label">ALL SKILLS</p>
        <V4Badge tone="info">{skills.length} built-in</V4Badge>
      </div>

      <ViewportBoundedPanel
        className="v4-recipe-catalog-panel builtin-skills-grid-panel"
        footer={
          <ListPaginator
            page={pagination.page}
            totalPages={pagination.totalPages}
            totalItems={pagination.totalItems}
            pageSize={pageSize}
            onPageChange={pagination.setPage}
          />
        }
      >
        <div className="hub-catalog-grid">
          {pagination.slice.map((skill) => (
            <article key={skill.slug} className="v4-dream-cycle-card flex h-full min-w-0 flex-col gap-3">
              <div className="flex min-w-0 items-start justify-between gap-2">
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="qs-card-title text-sm font-semibold text-(--qs-text)">{skill.title}</p>
                  <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
                    {primaryRoleLabel(skill.roles ?? [])}
                  </p>
                </div>
                <V4Badge tone="info" className="shrink-0">
                  builtin
                </V4Badge>
              </div>

              <p className="qs-card-body text-xs leading-relaxed text-(--qs-text-3)">{builtinSummary(skill)}</p>

              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
                <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
                <p className="qs-card-body mt-1 text-xs leading-relaxed text-(--qs-text-2)">
                  {builtinAgentUsage(skill)}
                </p>
              </div>

              <p className="qs-card-meta font-mono text-[11px] text-(--qs-text-3)">
                {skill.slug} · v{skill.version}
              </p>

              {(skill.keywords ?? []).length ? (
                <div className="qs-tag-row">
                  {skill.keywords.slice(0, 6).map((kw) => (
                    <V4Chip key={kw} type="span" variant="tag" title={kw}>
                      {kw}
                    </V4Chip>
                  ))}
                </div>
              ) : null}

              {(skill.roles ?? []).length ? (
                <div className="qs-tag-row">
                  {(skill.roles ?? []).slice(0, 4).map((role) => (
                    <V4Badge key={role} tone="purple">
                      {role.replaceAll("_", " ")}
                    </V4Badge>
                  ))}
                </div>
              ) : null}

              <div className="v4-dream-cycle-card-actions">
                <Link
                  href={`/manual#skill-${encodeURIComponent(skill.slug)}`}
                  className="qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem] gap-1.5"
                >
                  <BookOpenIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  View skill
                </Link>
              </div>
            </article>
          ))}
        </div>
      </ViewportBoundedPanel>
    </div>
  );
}
