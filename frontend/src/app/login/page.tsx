"use client";

import { Eye, EyeOff } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Icons } from "@/components/icons";
import { api } from "@/lib/api";

export default function LoginPage() {
  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-brand-950 p-4">
      <div
        className="absolute inset-0 scale-105 bg-cover bg-center opacity-40"
        style={{ backgroundImage: "url('/images/clinic-bg.png')" }}
        aria-hidden
      />
      <div className="absolute inset-0 bg-gradient-to-tr from-brand-950/80 via-brand-900/40 to-transparent" aria-hidden />

      <div className="relative mb-8 flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-400 text-brand-950">
          <Icons.Logo className="h-6 w-6" />
        </span>
        <span className="text-3xl font-bold tracking-tight text-white">Hospital AI Suite</span>
      </div>

      <Suspense>
        <SignInCard />
      </Suspense>

      <p className="relative mt-10 text-center text-[11px] text-brand-100/70">
        Accounts are created by an administrator. Pilot environment: synthetic data only.
      </p>
    </div>
  );
}

function SignInCard() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState("");

  useEffect(() => {
    // Already signed in? Skip the form.
    api
      .session()
      .then(({ user }) => user && router.replace(next))
      .catch(() => {});
    api
      .config()
      .then((c) => setBanner(c.environment_banner))
      .catch(() => {});
  }, [next, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(username.trim(), password);
      router.replace(next.startsWith("/") ? next : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setBusy(false);
    }
  }

  const input =
    "w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";

  return (
    <form
      onSubmit={submit}
      className="relative z-10 w-full max-w-[420px] rounded-2xl border border-white/20 bg-white/95 p-8 shadow-2xl backdrop-blur-md"
    >
      <h1 className="text-xl font-semibold text-slate-900">Staff sign in</h1>
      <p className="mb-6 text-xs text-slate-500">{banner || "Sign in to continue"}</p>

      {error && (
        <p className="mb-5 flex items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 p-3 text-sm text-rose-600">
          <Icons.Alert className="h-4 w-4 shrink-0" />
          {error}
        </p>
      )}

      <label className="mb-4 block text-sm font-medium text-slate-700">
        Username
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoFocus
          required
          className={`mt-1.5 ${input}`}
        />
      </label>
      <label className="mb-6 block text-sm font-medium text-slate-700">
        Password
        <span className="relative mt-1.5 block">
          <input
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className={`${input} pr-11`}
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </span>
      </label>

      <button
        disabled={busy || !username || !password}
        className="w-full rounded-lg bg-brand-700 py-3 font-semibold text-white shadow-md hover:bg-brand-800 disabled:opacity-60"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
