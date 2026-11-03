"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Icons } from "@/shared/ui/icons";
import { Card, Spinner } from "@/shared/ui/ui";
import { canOpen } from "../access";
import { useSession } from "./SessionProvider";

/**
 * Renders the page only if the signed-in user may open it (see ROUTE_PERMISSIONS in ../access.ts). The overview
 * redirects users without access to their own home (patients to /portal); other pages show a clear message.
 * The backend enforces the same permissions on every API call; this only keeps the UI honest.
 */
export function RouteGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, homePath } = useSession();
  const allowed = canOpen(user, pathname);
  const redirectHome = !allowed && pathname === "/" && homePath !== "/";

  useEffect(() => {
    if (redirectHome) router.replace(homePath);
  }, [redirectHome, homePath, router]);

  if (allowed) return <>{children}</>;
  if (redirectHome) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }
  return (
    <main className="mx-auto max-w-xl px-4 py-16 sm:px-8">
      <Card className="flex flex-col items-center gap-3 p-10 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-600">
          <Icons.Alert className="h-6 w-6" />
        </span>
        <h1 className="text-lg font-semibold text-slate-900">You don&apos;t have access to this page</h1>
        <p className="text-sm text-slate-500">
          Your account doesn&apos;t include this part of the suite. Ask an administrator if you need it.
        </p>
        <Link
          href={homePath}
          className="mt-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
        >
          Go to your home page
        </Link>
      </Card>
    </main>
  );
}
