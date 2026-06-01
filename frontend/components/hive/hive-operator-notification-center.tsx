"use client";

import { Bell, ChevronRight } from "lucide-react";
import Link from "next/link";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { formatHiveNotificationBadge } from "@/lib/hooks/use-hive-notification-badge";
import { useOperatorPendingSnapshot } from "@/lib/hooks/use-operator-pending-snapshot";
import { studioPendingActionHref, studioPendingApprovalsHref, supervisorSessionHref } from "@/lib/operator-pending-events";
import { localizePhrase } from "@/lib/ui-copy";
import type { DashboardSummary } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface HiveOperatorNotificationCenterProps {
  summary: DashboardSummary | null;
  className?: string;
}

/** Desktop sidebar notification center — Execution Studio + review pending items. */
export function HiveOperatorNotificationCenter({ summary, className }: HiveOperatorNotificationCenterProps) {
  const { language } = useUiLanguage();
  const snapshot = useOperatorPendingSnapshot(summary?.tasks.pending ?? 0);
  const badge = formatHiveNotificationBadge(snapshot.total);
  const open = snapshot.total > 0;

  return (
    <div className={cn("hidden lg:block", className)}>
      <details className="group rounded-xl border border-[color:var(--qs-border)]/60 bg-black/30" open={open}>
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2.5 [&::-webkit-details-marker]:hidden">
          <span className="flex min-w-0 items-center gap-2 text-xs font-semibold text-(--qs-text)">
            <Bell className="h-4 w-4 shrink-0 text-pollen" aria-hidden />
            {localizePhrase(language, { en: "Notifications", sk: "Notifikácie" })}
          </span>
          {badge ? (
            <span className="rounded-full bg-magenta px-2 py-0.5 font-mono text-[10px] font-semibold text-white">
              {badge}
            </span>
          ) : (
            <span className="text-[10px] text-(--qs-text-4)">
              {localizePhrase(language, { en: "All clear", sk: "Všetko OK" })}
            </span>
          )}
        </summary>

        <div className="space-y-2 border-t border-[color:var(--qs-border)]/40 px-3 py-2.5">
          {snapshot.tasksPending > 0 ? (
            <NotificationRow
              href="/tasks"
              label={localizePhrase(language, {
                en: `${snapshot.tasksPending} pending tasks`,
                sk: `${snapshot.tasksPending} čakajúcich úloh`,
              })}
            />
          ) : null}
          {snapshot.reviewPending > 0 ? (
            <NotificationRow
              href="/learning"
              label={localizePhrase(language, {
                en: `${snapshot.reviewPending} items to review`,
                sk: `${snapshot.reviewPending} položiek na review`,
              })}
            />
          ) : null}
          {snapshot.studioPending > 0 ? (
            <>
              <NotificationRow
                href={studioPendingApprovalsHref(snapshot.studio)}
                label={localizePhrase(language, {
                  en: `${snapshot.studioPending} Execution Studio approvals`,
                  sk: `${snapshot.studioPending} Execution Studio schválení`,
                })}
              />
              {(snapshot.studio.codebase_pending ?? 0) > 0 && snapshot.studio.live_actions.length === 0 ? (
                <p className="ml-1 text-[10px] text-(--qs-text-4)">
                  {localizePhrase(language, {
                    en: "SCV codebase proposals — open Lanes tab",
                    sk: "SCV codebase návrhy — záložka Lanes",
                  })}
                </p>
              ) : null}
              {snapshot.studio.live_actions.slice(0, 3).map((action) => (
                <NotificationRow
                  key={`${action.type}-${action.connector_slug ?? "browser"}-${action.message ?? ""}`}
                  href={
                    action.supervisor_session_id
                      ? supervisorSessionHref(action.supervisor_session_id)
                      : studioPendingActionHref(action)
                  }
                  label={action.message ?? action.type}
                  compact
                />
              ))}
            </>
          ) : null}
          {snapshot.total === 0 ? (
            <p className="text-[10px] text-(--qs-text-4)">
              {localizePhrase(language, {
                en: "No pending operator actions.",
                sk: "Žiadne čakajúce akcie operátora.",
              })}
            </p>
          ) : null}
        </div>
      </details>
    </div>
  );
}

function NotificationRow({ href, label, compact = false }: { href: string; label: string; compact?: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center justify-between gap-2 rounded-lg border border-[color:var(--qs-border)]/30 bg-black/20 px-2.5 py-2 text-(--qs-text-2) hover:border-pollen/30 hover:text-pollen",
        compact ? "ml-1 text-[10px] text-(--qs-text-3)" : "text-[11px]",
      )}
    >
      <span className="truncate">{label}</span>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
    </Link>
  );
}
