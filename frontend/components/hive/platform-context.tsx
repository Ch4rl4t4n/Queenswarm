"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { hiveGet } from "@/lib/api";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import type { DashboardOperatorMe } from "@/lib/hive-dashboard-session";
import {
  isFeatureEnabled,
  isRouteAllowed,
  normalizePlatformMode,
  resolvePlatformFeaturesFallback,
  type PlatformMode,
} from "@/lib/platform-features";
import type { TenantBrandingBrief } from "@/lib/tenant-branding";
import { isCustomTenantBranding, resolveTenantBranding } from "@/lib/tenant-branding";

export interface PlatformContextValue {
  loading: boolean;
  platformMode: PlatformMode;
  subscriptionTier: string;
  isAdmin: boolean;
  totpEnabled: boolean;
  displayName: string | null;
  email: string | null;
  features: Record<string, boolean>;
  tenantBranding: TenantBrandingBrief | null;
  hasFeature: (key: string) => boolean;
  isPathAllowed: (pathname: string) => boolean;
  refresh: () => Promise<void>;
}

const PlatformContext = createContext<PlatformContextValue | null>(null);

const DEFAULT_FEATURES = resolvePlatformFeaturesFallback({
  platformMode: "internal",
  isAdmin: true,
  subscriptionTier: "free",
});

export function PlatformProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [platformMode, setPlatformMode] = useState<PlatformMode>("internal");
  const [subscriptionTier, setSubscriptionTier] = useState("free");
  const [isAdmin, setIsAdmin] = useState(false);
  const [totpEnabled, setTotpEnabled] = useState(false);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [features, setFeatures] = useState<Record<string, boolean>>(DEFAULT_FEATURES);
  const [tenantBranding, setTenantBranding] = useState<TenantBrandingBrief | null>(null);

  const applyMe = useCallback((me: DashboardOperatorMe) => {
    const mode = normalizePlatformMode(me.platform_mode);
    const tier = String(me.subscription_tier ?? "free");
    const admin = Boolean(me.is_admin);
    setPlatformMode(mode);
    setSubscriptionTier(tier);
    setIsAdmin(admin);
    setTotpEnabled(Boolean(me.totp_enabled ?? me.totp_verified_at));
    setDisplayName(me.display_name ?? null);
    setEmail(me.email ?? null);
    setTenantBranding(me.tenant_branding ? resolveTenantBranding(me.tenant_branding) : null);
    if (me.platform_features && Object.keys(me.platform_features).length > 0) {
      setFeatures(me.platform_features);
    } else {
      setFeatures(
        resolvePlatformFeaturesFallback({
          platformMode: mode,
          isAdmin: admin,
          subscriptionTier: tier,
        }),
      );
    }
  }, []);

  useEffect(() => {
    if (!tenantBranding || !isCustomTenantBranding(tenantBranding)) {
      document.documentElement.style.removeProperty("--qs-tenant-accent");
      return;
    }
    document.documentElement.style.setProperty("--qs-tenant-accent", tenantBranding.accent_hex);
    return () => {
      document.documentElement.style.removeProperty("--qs-tenant-accent");
    };
  }, [tenantBranding]);

  const refresh = useCallback(async () => {
    try {
      const me = await hiveGet<DashboardOperatorMe>("auth/me");
      applyMe(me);
    } catch {
      /* offline — keep defaults */
    } finally {
      setLoading(false);
    }
  }, [applyMe]);

  useEffect(() => {
    if (!tenantBranding || !isCustomTenantBranding(tenantBranding)) {
      document.documentElement.style.removeProperty("--qs-tenant-accent");
      return;
    }
    document.documentElement.style.setProperty("--qs-tenant-accent", tenantBranding.accent_hex);
    return () => {
      document.documentElement.style.removeProperty("--qs-tenant-accent");
    };
  }, [tenantBranding]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh();
    }, DASHBOARD_BOOT_STAGGER_MS.platformMe);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const value = useMemo<PlatformContextValue>(
    () => ({
      loading,
      platformMode,
      subscriptionTier,
      isAdmin,
      totpEnabled,
      displayName,
      email,
      features,
      tenantBranding,
      hasFeature: (key: string) => isFeatureEnabled(features, key),
      isPathAllowed: (pathname: string) => isRouteAllowed(pathname, features),
      refresh,
    }),
    [loading, platformMode, subscriptionTier, isAdmin, totpEnabled, displayName, email, features, tenantBranding, refresh],
  );

  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
}

export function usePlatform(): PlatformContextValue {
  const ctx = useContext(PlatformContext);
  if (!ctx) {
    return {
      loading: false,
      platformMode: "internal",
      subscriptionTier: "free",
      isAdmin: true,
      totpEnabled: false,
      displayName: null,
      email: null,
      features: DEFAULT_FEATURES,
      tenantBranding: null,
      hasFeature: (key: string) => isFeatureEnabled(DEFAULT_FEATURES, key),
      isPathAllowed: (pathname: string) => isRouteAllowed(pathname, DEFAULT_FEATURES),
      refresh: async () => undefined,
    };
  }
  return ctx;
}
