"use client";

import { Bell, ChevronRight, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import { useOperatorMissionFeedContext } from "@/components/hive/operator-mission-feed-provider";
import { formatHiveNotificationBadge } from "@/lib/hooks/use-hive-notification-badge";
import { useOperatorPendingSnapshot } from "@/lib/hooks/use-operator-pending-snapshot";
import { studioPendingApprovalsHref, supervisorSessionHref } from "@/lib/operator-pending-events";
import type { DashboardSummary } from "@/lib/hive-types";
import { useModalA11y } from "@/lib/use-modal-a11y";
import { cn } from "@/lib/utils";

interface HiveMobileNotificationSheetProps {
  open: boolean;
  onClose: () => void;
  summary: DashboardSummary | null;
}

/** Mobile/tablet bottom sheet — mission feed + pending operator actions. */
export function HiveMobileNotificationSheet({
  open,
  onClose,
  summary,
}: HiveMobileNotificationSheetProps): JSX.Element | null {
  const panelRef = useRef<HTMLDivElement>(null);
  const missionFeed = useOperatorMissionFeedContext();
  const snapshot = useOperatorPendingSnapshot(summary?.tasks.pending ?? 0);

  useModalA11y({ open, onClose, containerRef: panelRef });

  useEffect(() => {
    if (open) {
      void missionFeed.refresh();
    }
  }, [open, missionFeed]);

  if (!open) {
    return null;
  }

  const unreadMission = missionFeed.events.filter((ev) => !ev.read);

  return (
    <div className="fixed inset-0 z-[130] lg:hidden" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
        aria-label="Close notifications"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="hive-mobile-notifications-title"
        className={cn(
          "absolute inset-x-0 bottom-0 max-h-[min(78vh,640px)] overflow-y-auto",
          "rounded-t-2xl border border-[color:var(--qs-border)] bg-[#0a0a0c] pb-[env(safe-area-inset-bottom)]",
          "shadow-[0_-12px_40px_rgba(0,0,0,0.55)]",
        )}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-[color:var(--qs-border)]/60 bg-[#0a0a0c]/95 px-4 py-3 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-pollen" aria-hidden />
            <h2
              id="hive-mobile-notifications-title"
              className="font-[family-name:var(--font-hive-display)] text-sm font-semibold text-(--qs-text)"
            >
              Notifications
            </h2>
            {formatHiveNotificationBadge(snapshot.total + missionFeed.unread) ? (
              <span className="rounded-full bg-magenta px-2 py-0.5 font-mono text-[10px] font-semibold text-white">
                {formatHiveNotificationBadge(snapshot.total + missionFeed.unread)}
              </span>
            ) : null}
          </div>
          <button
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-[color:var(--qs-border)] text-(--qs-text-3) hover:text-pollen touch-manipulation"
            aria-label="Close"
            onClick={onClose}
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <div className="space-y-4 px-4 py-4">
          {unreadMission.length > 0 ? (
            <section>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-pollen">Mission updates</p>
              <ul className="space-y-2">
                {unreadMission.slice(0, 8).map((ev) => (
                  <li key={ev.id}>
                    <Link
                      href={ev.href}
                      onClick={() => {
                        void missionFeed.dismiss([ev.id]);
                        onClose();
                      }}
                      className="flex items-start justify-between gap-2 rounded-xl border border-[color:var(--qs-border)]/40 bg-black/30 px-3 py-2.5 text-left hover:border-pollen/30"
                    >
                      <span className="min-w-0">
                        <span className="block text-xs font-semibold text-(--qs-text)">{ev.title}</span>
                        <span className="mt-0.5 block truncate text-[11px] text-(--qs-text-3)">{ev.body}</span>
                      </span>
                      <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-(--qs-text-4)" aria-hidden />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {snapshot.tasksPending > 0 ? (
            <section>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-cyan">Tasks</p>
              <SheetLink href="/tasks" label={`${snapshot.tasksPending} pending tasks`} onNavigate={onClose} />
            </section>
          ) : null}

          {snapshot.reviewPending > 0 ? (
            <section>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-cyan">Review</p>
              <SheetLink
                href="/learning"
                label={`${snapshot.reviewPending} items to review`}
                onNavigate={onClose}
              />
            </section>
          ) : null}

          {snapshot.studioPending > 0 ? (
            <section>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-cyan">Execution Studio</p>
              <SheetLink
                href={studioPendingApprovalsHref(snapshot.studio)}
                label={`${snapshot.studioPending} approvals waiting`}
                onNavigate={onClose}
              />
              {snapshot.studio.live_actions.slice(0, 3).map((action) => (
                <SheetLink
                  key={`${action.type}-${action.connector_slug ?? "browser"}`}
                  href={
                    action.supervisor_session_id
                      ? supervisorSessionHref(action.supervisor_session_id)
                      : studioPendingApprovalsHref(snapshot.studio)
                  }
                  label={action.message ?? action.type}
                  compact
                  onNavigate={onClose}
                />
              ))}
            </section>
          ) : null}

          {unreadMission.length === 0 && snapshot.total === 0 ? (
            <p
              data-testid="hive-mobile-notifications-empty"
              className="pt-16 pb-10 text-center text-sm leading-relaxed text-(--qs-text-4)"
            >
              No pending operator actions.
            </p>
          ) : null}

          <Link
            href="/settings/notifications"
            onClick={onClose}
            className="block text-center text-[11px] text-(--qs-text-4) underline-offset-2 hover:text-pollen hover:underline"
          >
            Notification settings
          </Link>
        </div>
      </div>
    </div>
  );
}

function SheetLink({
  href,
  label,
  compact = false,
  onNavigate,
}: {
  href: string;
  label: string;
  compact?: boolean;
  onNavigate: () => void;
}): JSX.Element {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={cn(
        "mb-2 flex items-center justify-between gap-2 rounded-xl border border-[color:var(--qs-border)]/40 bg-black/30 px-3 py-2.5 text-(--qs-text-2) hover:border-pollen/30 hover:text-pollen",
        compact ? "ml-1 text-[11px]" : "text-xs",
      )}
    >
      <span className="truncate">{label}</span>
      <ChevronRight className="h-4 w-4 shrink-0 opacity-70" aria-hidden />
    </Link>
  );
}
