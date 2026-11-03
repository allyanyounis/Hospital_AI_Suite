"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { UnauthorizedError } from "@/shared/api/http";
import { Spinner } from "@/shared/ui/ui";
import { authApi } from "../api";
import { hasPermission, homePath } from "../access";
import type { AppConfig, Permission, User } from "../types";

type Session = {
  user: User;
  config: AppConfig;
  signOut: () => Promise<void>;
  /** Whether the signed-in user holds a permission (null = any signed-in user) */
  can: (permission: Permission | null) => boolean;
  /** Where this user's "home" is: /portal for patients, / for staff */
  homePath: string;
};

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
    const toLogin = () => router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    Promise.all([authApi.config(), authApi.session()])
      .then(([config, { user }]) => (user ? setSession({ config, user }) : toLogin()))
      .catch((e) => (e instanceof UnauthorizedError ? toLogin() : setOffline(true)));
    // Only on first load; navigation between signed-in pages keeps the session
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signOut = useCallback(async () => {
    await authApi.logout().catch(() => {});
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
  return (
    <SignedIn user={session.user} config={session.config} signOut={signOut}>
      {children}
    </SignedIn>
  );
}

function SignedIn({
  user,
  config,
  signOut,
  children,
}: Pick<Session, "user" | "config" | "signOut"> & { children: React.ReactNode }) {
  const value = useMemo<Session>(
    () => ({ user, config, signOut, can: (p) => hasPermission(user, p), homePath: homePath(user) }),
    [user, config, signOut],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center bg-surface text-sm text-slate-500">{children}</div>;
}
