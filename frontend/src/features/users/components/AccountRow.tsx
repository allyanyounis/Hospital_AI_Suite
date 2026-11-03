"use client";

import { useState } from "react";
import { ROLE_LABELS, type Role, STAFF_ROLES } from "@/features/auth";
import { formatDate, initials } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Toggle } from "@/shared/ui/ui";
import { usersApi } from "../api";
import type { UserAccount } from "../types";
import { MIN_PASSWORD_LENGTH } from "./CreateAccountForm";

/** One account: role (staff only), enable/disable, password reset. Errors go to the parent's notice. */
export function AccountRow({
  account: a,
  isSelf,
  onChanged,
  onError,
  onNotice,
}: {
  account: UserAccount;
  isSelf: boolean;
  onChanged: (account: UserAccount) => void;
  onError: (message: string) => void;
  onNotice: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } catch (e) {
      onError(e instanceof Error ? e.message : "The change failed");
    } finally {
      setBusy(false);
    }
  }

  const changeRole = (role: Role) => run(async () => onChanged(await usersApi.update(a.username, { role })));
  const setActive = (active: boolean) => run(async () => onChanged(await usersApi.update(a.username, { active })));
  const resetPassword = () => {
    const password = prompt(`New password for ${a.display_name} (at least ${MIN_PASSWORD_LENGTH} characters):`);
    if (password === null) return;
    if (password.length < MIN_PASSWORD_LENGTH) {
      onError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
      return;
    }
    run(async () => {
      await usersApi.resetPassword(a.username, password);
      onNotice(`Password reset for ${a.display_name}.`);
    });
  };

  return (
    <tr className={`hover:bg-brand-50/40 ${a.active ? "" : "opacity-60"}`}>
      <td className="px-5 py-3">
        <div className="flex items-center gap-3">
          <Avatar text={initials(a.display_name)} size="sm" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {a.display_name}
              {isSelf && <span className="ml-1.5 text-xs font-normal text-slate-400">(you)</span>}
            </p>
            <p className="text-xs text-slate-500">
              <code>{a.username}</code> · since {formatDate(new Date(a.created_at))}
            </p>
          </div>
        </div>
      </td>
      <td className="px-3 py-3 text-sm">
        {a.role === "patient" ? (
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">Patient</span>
        ) : (
          <select
            value={a.role}
            disabled={busy || isSelf}
            title={isSelf ? "You can't change your own role" : "Change role"}
            onChange={(e) => changeRole(e.target.value as Role)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm text-slate-800 outline-none focus:border-brand-700 disabled:opacity-60"
          >
            {STAFF_ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        )}
      </td>
      <td className="px-3 py-3 text-sm text-slate-600">
        {a.patient ? (
          <>
            {a.patient.name}
            {a.patient.mrn && <span className="block text-xs text-slate-400">MRN {a.patient.mrn}</span>}
          </>
        ) : (
          <span className="text-slate-300">—</span>
        )}
      </td>
      <td className="px-3 py-3">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {isSelf ? (
            <span className="font-semibold text-emerald-600">Active</span>
          ) : (
            <>
              <Toggle checked={a.active} label={`${a.display_name} active`} onChange={(v) => !busy && setActive(v)} />
              {a.active ? "Active" : "Disabled"}
            </>
          )}
        </div>
      </td>
      <td className="px-5 py-3 text-right">
        <button
          onClick={resetPassword}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <Icons.Key className="h-3.5 w-3.5" /> Reset password
        </button>
      </td>
    </tr>
  );
}
