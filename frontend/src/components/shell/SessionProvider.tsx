"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Spinner } from "@/components/ui";
import { api, UnauthorizedError, type AppConfig, type User } from "@/lib/api";

type Session = { user: User; config: AppConfig; signOut: () => Promise<void> };

const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside SessionProvider");
  return session;
}

/** Loads the signed-in user; sends anyone signed out to /login (and back here afterwards). */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<{ user: User; config: AppConfig } | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    Promise.all([api.config(), api.me()])
      .then(([config, user]) => setSession({ config, user }))
      .catch((e) => {
        if (e instanceof UnauthorizedError) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        else setOffline(true);
      });
    // Only on first load; navigation between signed-in pages keeps the session
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signOut = useCallback(async () => {
    await api.logout().catch(() => {});
    router.replace("/login");
  }, [router]);

  if (offline) {
    return <Centered>Can&apos;t reach the backend. Is it running on port 8000?</Centered>;
  }
  if (!session) {
    return (
      <Centered>
        <Spinner className="h-8 w-8" />
      </Centered>
    );
  }
  return <SessionContext.Provider value={{ ...session, signOut }}>{children}</SessionContext.Provider>;
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center bg-surface text-sm text-slate-500">{children}</div>;
}
