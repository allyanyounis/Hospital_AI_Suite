"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Icons } from "@/components/icons";
import { isActive, NAVIGATION } from "./navigation";
import { useSession } from "./SessionProvider";

/** Signed-in layout: maroon sidebar with both modules, top bar with patient search and quick actions. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen bg-surface">
      <Sidebar pathname={pathname} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar pathname={pathname} />
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

function Sidebar({ pathname }: { pathname: string }) {
  const { user, config, signOut } = useSession();

  return (
    <aside className="hidden w-64 shrink-0 flex-col overflow-y-auto bg-gradient-to-b from-brand-900 to-brand-950 text-brand-100 md:flex">
      <div className="flex items-center gap-3 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-400 text-brand-950">
          <Icons.Logo className="h-5 w-5" />
        </span>
        <div>
          <p className="text-base font-bold leading-tight text-white">Hospital AI Suite</p>
          <p className="text-[11px] leading-tight text-brand-200/70">Scribe · Receptionist</p>
        </div>
      </div>

      <nav className="flex-1">
        {NAVIGATION.map((group) => (
          <div key={group.title} className="px-3 pb-4">
            <p className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-brand-200/50">{group.title}</p>
            <ul className="space-y-1">
              {group.items.map(({ href, label, icon: Icon }) => (
                <li key={href}>
                  <Link
                    href={href}
                    className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${
                      isActive(pathname, href)
                        ? "bg-amber-400 text-brand-950 shadow-sm"
                        : "text-brand-100/85 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <Icon className="h-[18px] w-[18px]" />
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="mb-3 space-y-1.5 text-[11px]">
          <ServiceStatus ok={config.transcriber_ready} label={`Speech: ${config.transcriber}`} />
          <ServiceStatus ok={config.notes_ready} label={`Notes: ${config.note_model}`} />
        </div>
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-400 text-sm font-bold text-brand-950">
            {user.display_name
              .replace(/^Dr\.?\s*/i, "")
              .slice(0, 1)
              .toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-white">{user.display_name}</p>
            <p className="text-[11px] capitalize text-brand-200/70">{user.role}</p>
          </div>
          <button
            onClick={signOut}
            title="Sign out"
            className="rounded-md p-1.5 text-brand-200 hover:bg-white/10 hover:text-white"
          >
            <Icons.Logout />
          </button>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ pathname }: { pathname: string }) {
  const router = useRouter();
  const { config } = useSession();
  const [query, setQuery] = useState("");

  return (
    <header className="flex items-center gap-3 border-b border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur sm:px-6">
      {/* Compact icon nav for small screens */}
      <nav className="flex gap-1 overflow-x-auto md:hidden">
        {NAVIGATION.flatMap((g) => g.items).map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            title={label}
            className={`rounded-lg p-2 ${isActive(pathname, href) ? "bg-brand-700 text-white" : "text-slate-500"}`}
          >
            <Icon />
          </Link>
        ))}
      </nav>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          router.push(`/scribe/encounters?q=${encodeURIComponent(query.trim())}`);
        }}
        className="relative hidden max-w-xl flex-1 sm:block"
      >
        <Icons.Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search encounters by patient name or MRN…"
          className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none focus:border-brand-600 focus:bg-white"
        />
      </form>
      <span className="ml-auto hidden text-xs text-slate-500 lg:inline">{config.environment_banner}</span>
      <Link
        href="/reception/agent"
        className="hidden items-center gap-1.5 rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50 sm:flex"
      >
        <Icons.Phone />
        Voice Agent
      </Link>
      <Link
        href="/scribe/session"
        className="flex items-center gap-1.5 rounded-xl bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800"
      >
        <Icons.Plus />
        New Session
      </Link>
    </header>
  );
}

function ServiceStatus({ ok, label }: { ok: boolean; label: string }) {
  return (
    <p
      className="flex items-center gap-2 truncate text-brand-100/80"
      title={ok ? "Configured" : "Not configured in backend/.env"}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${ok ? "bg-emerald-400" : "bg-amber-400"}`} />
      <span className="truncate">
        {label}
        {!ok && " (not ready)"}
      </span>
    </p>
  );
}
