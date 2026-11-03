"use client";

import { useEffect, useState } from "react";
import { ROLE_LABELS, type Role, STAFF_ROLES, useSession } from "@/features/auth";
import { StaffProfileForm } from "@/features/staff";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { usersApi } from "../api";
import { AccountRow } from "../components/AccountRow";
import { CreateAccountForm } from "../components/CreateAccountForm";
import type { UserAccount } from "../types";

type Filter = "all" | Role;
const FILTERS: Filter[] = ["all", ...STAFF_ROLES, "patient"];

/** Admin: every account, its role and status; create staff (then their hospital profile) and patient accounts. */
export function UsersView() {
  const { user } = useSession();
  const [accounts, setAccounts] = useState<UserAccount[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  // A staff account just created: its hospital profile (department, title, bookable) is the next step
  const [profileFor, setProfileFor] = useState<UserAccount | null>(null);

  useEffect(() => {
    usersApi
      .list()
      .then(setAccounts)
      .catch((e) => {
        setAccounts([]);
        setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load accounts" });
      });
  }, []);

  const upsert = (account: UserAccount) =>
    setAccounts((list) => {
      const rest = (list ?? []).filter((a) => a.username !== account.username);
      return [...rest, account].sort((a, b) => a.username.localeCompare(b.username));
    });

  const shown = (accounts ?? []).filter((a) => filter === "all" || a.role === filter);
  const count = (role: Role) => (accounts ?? []).filter((a) => a.role === role).length;

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Users className="h-6 w-6" />}
        title="Users"
        subtitle="Who can sign in, and as what. Doctors, nurses and receptionists each see their part of the hospital; admins also manage accounts, departments and staff; patients see only their own appointments."
      />
      {notice && <Notice tone={notice.ok ? "success" : "error"}>{notice.text}</Notice>}

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  filter === f ? "bg-brand-700 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {f === "all" ? `All (${accounts?.length ?? 0})` : `${ROLE_LABELS[f]}s (${count(f)})`}
              </button>
            ))}
          </div>
          {accounts === null ? (
            <div className="flex justify-center py-12">
              <Spinner className="h-6 w-6" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left">
                <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-2.5">Name</th>
                    <th className="px-3 py-2.5">Role</th>
                    <th className="px-3 py-2.5">Patient record</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-5 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shown.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-10 text-center text-sm text-slate-400">
                        No accounts here yet.
                      </td>
                    </tr>
                  ) : (
                    shown.map((a) => (
                      <AccountRow
                        key={a.username}
                        account={a}
                        isSelf={a.username === user.username}
                        onChanged={(changed) => {
                          upsert(changed);
                          setNotice({ ok: true, text: `Saved ${changed.display_name}.` });
                        }}
                        onError={(text) => setNotice({ ok: false, text })}
                        onNotice={(text) => setNotice({ ok: true, text })}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {profileFor ? (
          <Card className="p-5">
            <p className="text-sm font-semibold text-slate-900">Staff profile · {profileFor.display_name}</p>
            <p className="mb-4 text-xs text-slate-500">
              Their department and role in the hospital. Bookable doctors get an OPD schedule and take appointments.
            </p>
            <StaffProfileForm
              username={profileFor.username}
              suggestBookable={profileFor.role === "doctor"}
              onCancel={() => setProfileFor(null)}
              onSaved={(member) => {
                setProfileFor(null);
                setNotice({ ok: true, text: `Saved ${member.display_name}'s profile in ${member.department.name}.` });
              }}
            />
          </Card>
        ) : (
          <CreateAccountForm
            onCreated={(account) => {
              upsert(account);
              setNotice({ ok: true, text: `Created ${ROLE_LABELS[account.role].toLowerCase()} account ${account.username}.` });
              if (account.role !== "patient") setProfileFor(account);
            }}
          />
        )}
      </div>
    </main>
  );
}
