"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { Toaster } from "@/components/ui/sonner";

/** Mock via MSW: ligado em dev, salvo se explicitamente desabilitado. */
const shouldMock =
  process.env.NODE_ENV === "development" &&
  process.env.NEXT_PUBLIC_API_MOCKING !== "disabled";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
        },
      }),
  );
  // Só bloqueia o render até o worker subir quando o mock está ligado.
  const [ready, setReady] = React.useState(!shouldMock);

  React.useEffect(() => {
    if (!shouldMock) return;
    let active = true;
    import("@/lib/mock/init")
      .then((m) => m.enableMocking())
      .then(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  if (!ready) return null;

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  );
}
