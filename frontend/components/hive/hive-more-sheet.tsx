"use client";

import { LockIcon, LogOutIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef } from "react";
import { toast } from "sonner";

import { HiveAccountIdentity } from "@/components/hive/hive-account-identity";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { usePlatform } from "@/components/hive/platform-context";
import { HIVE_NAV_GROUPS, isNavItemActive } from "@/lib/hive-nav-primary";
import { filterNavGroupsByFeatures } from "@/lib/platform-features";
import { useRouteHash } from "@/lib/hooks/use-route-hash";
import type { TenantListPayload } from "@/lib/hive-types";
import { clearExecutionStudioPushOnLogout } from "@/lib/execution-studio-push-session-sync";
import { useModalA11y } from "@/lib/use-modal-a11y";
import { localizeNavLabel, localizePhrase } from "@/lib/ui-copy";
import { cn } from "@/lib/utils";

interface HiveMoreSheetProps {
  open: boolean;
  onClose: () => void;
  pathname: string;
  tenants?: TenantListPayload | null;
}

function tenantSubtitle(tenant: { role: string; platform_mode?: string }, language: "en" | "sk"): string {
  const role = tenant.role.replace(/_/g, " ");
  const cap = role.charAt(0).toUpperCase() + role.slice(1);
  const mode = tenant.platform_mode === "commercial" ? "commercial" : "operator";
  return localizePhrase(language, {
    en: `${cap} · ${mode}`,
    sk: `${cap} · ${mode}`,
  });
}

/** Full IA overflow — grouped routes + account actions (mobile / tablet). */
export function HiveMoreSheet({ open, onClose, pathname, tenants }: HiveMoreSheetProps) {
  const router = useRouter();
  const { language } = useUiLanguage();
  const { features } = usePlatform();
  const routeHash = useRouteHash();
  const navGroups = filterNavGroupsByFeatures(HIVE_NAV_GROUPS, features);
  const navCandidates = navGroups.flatMap((group) => group.items);
  const tenantList = tenants?.tenants ?? [];
  const currentTenant =
    tenantList.find((t) => t.id === tenants?.current_tenant_id) ?? tenantList[0] ?? null;
  const sheetRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useModalA11y({
    open,
    onClose,
    containerRef: sheetRef,
    initialFocusRef: closeRef,
  });

  async function logout(): Promise<void> {
    try {
      await clearExecutionStudioPushOnLogout();
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch {
      /* ignore */
    }
    toast.success(localizePhrase(language, { en: "Logged out", sk: "Odhlásené" }));
    onClose();
    router.push("/login");
    router.refresh();
  }

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[60] flex flex-col justify-end lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-black/72 backdrop-blur-sm"
        aria-label={localizePhrase(language, { en: "Close menu", sk: "Zavrieť menu" })}
        onClick={onClose}
      />
      <div
        ref={sheetRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="hive-more-sheet-title"
        className="relative mx-auto flex max-h-[min(88vh,640px)] w-full max-w-lg flex-col rounded-t-3xl border border-[color:var(--qs-border)] bg-[#0f0f16] shadow-[0_-24px_64px_rgb(0_0_0/0.55)]"
      >
        <div className="relative flex flex-col items-center px-4 pt-3">
          <span className="mb-2 h-1 w-14 rounded-full bg-zinc-600" aria-hidden />
          <button
            ref={closeRef}
            type="button"
            aria-label={localizePhrase(language, { en: "Close sheet", sk: "Zavrieť panel" })}
            className="absolute right-3 top-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] border border-[color:var(--qs-border)] text-zinc-400 hover:border-[color:var(--qs-border-2)] hover:text-pollen touch-manipulation"
            onClick={onClose}
          >
            <XIcon className="h-5 w-5" aria-hidden strokeWidth={2} />
          </button>
        </div>

        <h2 id="hive-more-sheet-title" className="px-6 pb-2 pt-1 font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
          {localizePhrase(language, { en: "Hive navigation", sk: "Hive navigácia" })}
        </h2>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-2 hive-scrollbar">
          {navGroups.map((group) => (
            <div key={group.title} className="mb-4">
              <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-600">
                {localizeNavLabel(group.title, language)}
              </p>
              <ul className="space-y-1">
                {group.items.map((item) => {
                  const { href, label, Icon } = item;
                  const active = isNavItemActive(pathname, item, { hash: routeHash, candidates: navCandidates });
                  return (
                    <li key={`${group.title}-${href}`}>
                      <Link
                        href={href}
                        prefetch
                        onClick={onClose}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "flex items-center gap-3 rounded-2xl px-4 py-3 font-[family-name:var(--font-poppins)] text-sm transition touch-manipulation min-h-[48px]",
                          active ? "bg-pollen/12 text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.25)]" : "text-zinc-300 hover:bg-white/[0.04]",
                        )}
                      >
                        <Icon className={cn("h-5 w-5 shrink-0", active ? "text-pollen" : "text-zinc-500")} aria-hidden />
                        <span className="leading-normal">{localizeNavLabel(label, language)}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-[color:var(--qs-border)] px-3 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-2">
          {currentTenant ? (
            <div className="mx-1 mb-3 rounded-2xl border border-[color:var(--qs-border)] bg-black/35 px-3 py-3">
              <HiveAccountIdentity
                name={currentTenant.name}
                subtitle={tenantSubtitle(currentTenant, language)}
                language={language}
              />
            </div>
          ) : null}
          <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-600">
            {localizePhrase(language, { en: "Session", sk: "Relácia" })}
          </p>
          <ul className="space-y-1">
            <li>
              <button
                type="button"
                className="flex w-full min-h-[48px] items-center gap-4 rounded-2xl px-4 py-3 text-left font-[family-name:var(--font-poppins)] text-sm text-zinc-300 transition hover:bg-white/[0.04] touch-manipulation"
                onClick={() => {
                  onClose();
                  router.push("/login");
                }}
              >
                <LockIcon className="h-5 w-5 shrink-0 text-pollen" aria-hidden />
                {localizePhrase(language, { en: "Login screen", sk: "Prihlasovacia obrazovka" })}
              </button>
            </li>
            <li>
              <button
                type="button"
                className="flex w-full min-h-[48px] items-center gap-4 rounded-2xl px-4 py-3 text-left font-[family-name:var(--font-poppins)] text-sm text-danger transition hover:bg-danger/[0.08] touch-manipulation"
                onClick={() => void logout()}
              >
                <LogOutIcon className="h-5 w-5 shrink-0" aria-hidden />
                {localizePhrase(language, { en: "Log out", sk: "Odhlásiť" })}
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
