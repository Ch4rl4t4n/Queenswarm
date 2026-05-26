"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";
import { SWRConfig } from "swr";
import { Toaster } from "sonner";

import { UiLanguageProvider } from "@/components/hive/ui-language-provider";
import { HiveInstallPrompt } from "@/components/hive/hive-install-prompt";
import { HiveOfflineBanner } from "@/components/hive/hive-offline-banner";
import { HiveServiceWorker } from "@/components/hive/hive-service-worker";

interface ProvidersProps {
  children: ReactNode;
}

const SWR_DEFAULTS = {
  dedupingInterval: 5_000,
  keepPreviousData: true,
  revalidateOnFocus: false,
  errorRetryCount: 2,
} as const;

export function Providers({ children }: ProvidersProps) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <SWRConfig value={SWR_DEFAULTS}>
        <UiLanguageProvider>
          <HiveServiceWorker />
          <HiveOfflineBanner />
          <HiveInstallPrompt />
          {children}
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              className: "font-[family-name:var(--font-poppins)] text-sm",
              style: {
                background: "#050510",
                border: "1px solid rgba(0,255,255,0.25)",
                color: "#FFB800",
              },
            }}
          />
        </UiLanguageProvider>
      </SWRConfig>
    </QueryClientProvider>
  );
}
