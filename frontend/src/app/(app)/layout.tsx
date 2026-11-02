"use client";

import { AppShell } from "@/components/shell/AppShell";
import { SessionProvider } from "@/components/shell/SessionProvider";

/** Every page in this group requires sign-in and renders inside the sidebar layout. */
export default function SignedInLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AppShell>{children}</AppShell>
    </SessionProvider>
  );
}
