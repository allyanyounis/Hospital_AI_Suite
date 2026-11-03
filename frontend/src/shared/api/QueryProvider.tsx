"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { makeQueryClient } from "./queryClient";

/** One query client per browser tab (kept across navigation). A 401 from any query sends the user to sign in. */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [client] = useState(() =>
    makeQueryClient(() => {
      const here = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(here)}`);
    }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
