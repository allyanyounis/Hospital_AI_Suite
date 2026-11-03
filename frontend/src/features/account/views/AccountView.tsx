"use client";

import { useState } from "react";
import { ROLE_LABELS, type Role, useSession } from "@/features/auth";
import { initials } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, PageHeader } from "@/shared/ui/ui";
import { ChangePasswordForm } from "../components/ChangePasswordForm";

const ROLE_DESCRIPTIONS: Record<Role, string> = {
  admin: "Administrator: accounts, departments, staff and OPD schedules, plus hospital-wide metrics and call costs",
  doctor: "Doctor: the AI scribe for your own encounters, plus patients, appointments and OPD schedules",
  nurse: "Nurse: patients, appointments, OPD schedules and the staff directory (view only)",
  receptionist: "Receptionist: register patients, and book and cancel appointments",
  patient: "Patient: your own details and appointments",
};

export function AccountView() {
  const { user, config, can, signOut } = useSession();
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  const rows: [string, React.ReactNode][] = [
    ["Display name", user.display_name],
    [
      "Username",
      <code key="u" className="rounded bg-slate-100 px-1.5 py-0.5 text-sm">
        {user.username}
      </code>,
    ],
    ["Role", ROLE_LABELS[user.role] ?? user.role],
    ["Hospital", config.hospital_name || "—"],
    ["Hospital timezone", config.hospital_timezone],
    ...(can("scribe.use") ? [["Clinical content retention", `${config.retention_days} days`] as [string, React.ReactNode]] : []),
  ];

  return (
    <main className="mx-auto max-w-3xl space-y-5 px-4 py-6 sm:px-8">
      <PageHeader icon={<Icons.User className="h-6 w-6" />} title="Account" subtitle="Your sign-in details and access." />

      <Card>
        <div className="flex items-center gap-4 border-b border-slate-100 p-6">
          <Avatar text={initials(user.display_name)} />
          <div>
            <p className="text-lg font-semibold text-slate-900">{user.display_name}</p>
            <p className="text-sm text-slate-500">{ROLE_DESCRIPTIONS[user.role] ?? user.role}</p>
          </div>
        </div>
        <dl className="divide-y divide-slate-100">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-center justify-between px-6 py-3.5 text-sm">
              <dt className="text-slate-500">{label}</dt>
              <dd className="font-medium text-slate-900">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 p-6">
          <p className="text-xs text-slate-500">
            {can("users.manage") ? (
              <>Manage accounts under Administration → Users.</>
            ) : (
              <>Accounts are created by an administrator. Forgotten your password? Ask an administrator to reset it.</>
            )}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPasswordForm((v) => !v)}
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <Icons.Key className="h-4 w-4" /> Change password
            </button>
            <button
              onClick={signOut}
              className="flex items-center gap-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
            >
              <Icons.Logout /> Sign out
            </button>
          </div>
        </div>
      </Card>

      {showPasswordForm && <ChangePasswordForm onDone={() => setShowPasswordForm(false)} />}
    </main>
  );
}
