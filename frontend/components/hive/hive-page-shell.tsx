import type { ReactNode } from "react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { HivePageErrorBanner } from "@/components/hive/hive-page-error-banner";
import { V4PageCanvas } from "@/components/ui/v4";
import { hivePageHintProps, type HivePageHintKey } from "@/lib/hive-page-hints";
import type { HivePageShellErrorProps } from "@/lib/hive-page-error";
import { cn } from "@/lib/utils";

export interface HivePageShellProps {
  /** Primary page title (h1). */
  title: string;
  /** Muted description under the title. */
  subtitle?: ReactNode;
  /** Section hint registry key — renders inline (i) help next to subtitle. */
  hintKey?: HivePageHintKey;
  /** Right-aligned status pill (sync, policy pack, etc.). */
  status?: ReactNode;
  /** Primary page actions below the description row. */
  actions?: ReactNode;
  /** Sub-navigation row (HiveSubnavRow, HiveSectionSubnav wrapper, etc.). */
  subnav?: ReactNode;
  /** Optional inline alert below subnav (errors, sync notices, dismiss/retry). */
  error?: HivePageShellErrorProps | null;
  /** Renders above the page header (sync banners, mobile alerts). */
  banner?: ReactNode;
  children: ReactNode;
  className?: string;
  canvasClassName?: string;
  /** E2E anchor — defaults to `hive-page-shell`. */
  testId?: string;
}

/**
 * Unified page shell — header + optional subnav + content on V4PageCanvas.
 * Use on every top-level zone route for consistent rhythm (Whole-App UI Reorder phase 2).
 */
export function HivePageShell({
  title,
  subtitle,
  hintKey,
  status,
  actions,
  subnav,
  error,
  banner,
  children,
  className,
  canvasClassName,
  testId = "hive-page-shell",
}: HivePageShellProps) {
  return (
    <V4PageCanvas className={cn("min-w-0 max-w-full overflow-x-hidden", canvasClassName)} data-testid={testId}>
      {banner}
      <HivePageHeader
        title={title}
        subtitle={subtitle}
        info={hintKey ? hivePageHintProps(hintKey) : undefined}
        status={status}
        actions={actions}
        className={className}
      />
      {subnav ? (
        <div className="hive-page-shell-subnav min-w-0 max-w-full shrink-0 overflow-x-hidden">{subnav}</div>
      ) : null}
      {error ? (
        <HivePageErrorBanner
          message={error.message}
          tone={error.tone}
          onDismiss={error.onDismiss}
          onRetry={error.onRetry}
          retryBusy={error.retryBusy}
          testId={error.testId}
        />
      ) : null}
      <div
        className={cn(
          "hive-page-shell-content flex min-h-0 min-w-0 max-w-full flex-1 flex-col gap-6 overflow-x-hidden",
          subnav ? "mt-0" : undefined,
        )}
      >
        {children}
      </div>
    </V4PageCanvas>
  );
}
