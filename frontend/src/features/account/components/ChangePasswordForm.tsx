"use client";

import { useState } from "react";
import { changePassword } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, Spinner } from "@/shared/ui/ui";

const MIN_PASSWORD_LENGTH = 10;
const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";

/** Change your own password. The server re-issues the session cookie, so the user stays signed in. */
export function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  const mismatch = repeat.length > 0 && next !== repeat;
  const tooShort = next.length > 0 && next.length < MIN_PASSWORD_LENGTH;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setRepeat("");
      setResult({ ok: true, text: "Password changed." });
      setTimeout(onDone, 1500);
    } catch (err) {
      setResult({ ok: false, text: err instanceof Error ? err.message : "Could not change the password" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-6">
      <p className="mb-4 text-sm font-semibold text-slate-900">Change password</p>
      {result && (
        <div className="mb-4">
          <Notice tone={result.ok ? "success" : "error"}>{result.text}</Notice>
        </div>
      )}
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-3">
        <label className="block text-xs font-semibold text-slate-600">
          Current password
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            required
            className={field}
          />
        </label>
        <label className="block text-xs font-semibold text-slate-600">
          New password
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            required
            className={field}
          />
          {tooShort && <span className="mt-1 block font-normal text-rose-600">At least {MIN_PASSWORD_LENGTH} characters.</span>}
        </label>
        <label className="block text-xs font-semibold text-slate-600">
          Repeat new password
          <input
            type="password"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
            autoComplete="new-password"
            required
            className={field}
          />
          {mismatch && <span className="mt-1 block font-normal text-rose-600">Passwords don&apos;t match.</span>}
        </label>
        <div className="sm:col-span-3">
          <button
            disabled={busy || !current || next.length < MIN_PASSWORD_LENGTH || next !== repeat}
            className="flex items-center gap-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
          >
            {busy ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Check />}
            Save new password
          </button>
        </div>
      </form>
    </Card>
  );
}
