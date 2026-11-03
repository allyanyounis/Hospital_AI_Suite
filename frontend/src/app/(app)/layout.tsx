"use client";

import { RouteGuard, SessionProvider, useSession } from "@/features/auth";
import { AppShell } from "@/features/shell";
import { QueryProvider } from "@/shared/api/QueryProvider";
import { LiveEventsProvider } from "@/shared/live";

/** Every page in this group requires sign-in, is checked against the route map, and renders in the sidebar layout. */
export default function SignedInLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <QueryProvider>
        <SessionLiveEvents>
          <AppShell>
            <RouteGuard>{children}</RouteGuard>
          </AppShell>
        </SessionLiveEvents>
      </QueryProvider>
    </SessionProvider>
  );
}

/** The live-events socket requires appointments.view, so only users holding it connect. */
function SessionLiveEvents({ children }: { children: React.ReactNode }) {
  const { can } = useSession();
  return <LiveEventsProvider enabled={can("appointments.view")}>{children}</LiveEventsProvider>;
}
