"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";
import { Toaster } from "sonner";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            refetchOnWindowFocus: true,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      {children}
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          className: "font-[family-name:var(--font-jetbrains-mono)] text-sm",
          style: {
            background: "#050510",
            border: "1px solid rgba(0,255,255,0.25)",
            color: "#FFB800",
          },
        }}
      />
    </QueryClientProvider>
  );
}
