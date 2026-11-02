"use client";

import { Icons } from "@/components/icons";
import { useSession } from "@/components/shell/SessionProvider";
import { Avatar, Card, PageHeader } from "@/components/ui";
import { initials } from "@/lib/format";

export default function AccountPage() {
  const { user, config, signOut } = useSession();

  const rows: [string, React.ReactNode][] = [
    ["Display name", user.display_name],
    [
      "Username",
      <code key="u" className="rounded bg-slate-100 px-1.5 py-0.5 text-sm">
        {user.username}
      </code>,
    ],
    [
      "Role",
      <span key="r" className="capitalize">
        {user.role}
      </span>,
    ],
    ["Clinic timezone", config.clinic_timezone],
    ["Clinical content retention", `${config.retention_days} days`],
  ];

  return (
    <main className="mx-auto max-w-3xl px-4 py-6 sm:px-8">
      <PageHeader icon={<Icons.User className="h-6 w-6" />} title="Account" subtitle="Your sign-in details and access." />

      <Card>
        <div className="flex items-center gap-4 border-b border-slate-100 p-6">
          <Avatar text={initials(user.display_name)} />
          <div>
            <p className="text-lg font-semibold text-slate-900">{user.display_name}</p>
            <p className="text-sm text-slate-500">
              {user.role === "admin" ? "Administrator: sees hospital-wide pilot metrics" : "Clinician"}
            </p>
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
            Accounts and passwords are managed by an administrator:{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5">python -m app.users reset-password {user.username}</code>
          </p>
          <button
            onClick={signOut}
            className="flex items-center gap-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
          >
            <Icons.Logout /> Sign out
          </button>
        </div>
      </Card>
    </main>
  );
}
