"use client";

import { useEffect, useState } from "react";
import { ROLE_LABELS, useSession } from "@/features/auth";
import { type Department, departmentsApi } from "@/features/organization";
import { initials } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Avatar, Card, EmptyState, Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { staffApi } from "../api";
import { StaffProfileForm } from "../components/StaffProfileForm";
import type { StaffMember } from "../types";

/** The hospital's people by department. With staff.manage, each profile can be edited in place. */
export function StaffView() {
  const canManage = useSession().can("staff.manage");
  const [staff, setStaff] = useState<StaffMember[] | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentId, setDepartmentId] = useState<number | "all">("all");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<StaffMember | null>(null);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    staffApi
      .list()
      .then(setStaff)
      .catch((e) => {
        setStaff([]);
        setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load the staff directory" });
      });
    departmentsApi
      .list()
      .then(setDepartments)
      .catch(() => {});
  }, []);

  const q = query.trim().toLowerCase();
  const shown = (staff ?? []).filter(
    (m) =>
      (departmentId === "all" || m.department.id === departmentId) &&
      (!q || [m.display_name, m.username, m.specialty, m.job_title].some((v) => v.toLowerCase().includes(q))),
  );
  const byDepartment = new Map<string, StaffMember[]>();
  for (const m of shown) byDepartment.set(m.department.name, [...(byDepartment.get(m.department.name) ?? []), m]);
  const groups = [...byDepartment.entries()].sort(([a], [b]) => a.localeCompare(b));

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.UserCog className="h-6 w-6" />}
        title="Staff"
        subtitle="Doctors, nurses and front-desk staff by department. Bookable doctors have OPD schedules and take appointments."
        aside={
          <div className="flex flex-wrap gap-2">
            <select
              id="staff-department-filter"
              aria-label="Department"
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value === "all" ? "all" : Number(e.target.value))}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-brand-700"
            >
              <option value="all">All departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
              <Icons.Search className="h-4 w-4 text-slate-400" />
              <input
                id="staff-search"
                aria-label="Search staff"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Name or specialty…"
                className="w-40 bg-transparent text-sm outline-none"
              />
            </div>
          </div>
        }
      />
      {notice && <Notice tone={notice.ok ? "success" : "error"}>{notice.text}</Notice>}
      {canManage && (
        <p className="text-xs text-slate-500">
          New staff accounts are created under Hospital → Users; their profile can then be set here.
        </p>
      )}

      {editing && (
        <Card className="p-5">
          <p className="mb-3 text-sm font-semibold text-slate-900">Edit profile · {editing.display_name}</p>
          <StaffProfileForm
            username={editing.username}
            current={editing}
            onCancel={() => setEditing(null)}
            onSaved={(member) => {
              setStaff((list) => (list ?? []).map((m) => (m.username === member.username ? member : m)));
              setEditing(null);
              setNotice({ ok: true, text: `Saved ${member.display_name}'s profile.` });
            }}
          />
        </Card>
      )}

      {staff === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : groups.length === 0 ? (
        <Card>
          <EmptyState icon={<Icons.UserCog />} title="No staff found">
            {staff.length === 0 ? "No staff profiles yet." : "Nobody matches this filter."}
          </EmptyState>
        </Card>
      ) : (
        groups.map(([department, members]) => (
          <Card key={department} className="overflow-hidden">
            <p className="border-b border-slate-100 bg-brand-50/50 px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-brand-700">
              {department}
              <span className="ml-2 font-normal normal-case text-slate-400">
                {members.length} {members.length === 1 ? "person" : "people"}
              </span>
            </p>
            <ul className="divide-y divide-slate-100">
              {members.map((m) => (
                <li key={m.id} className={`flex flex-wrap items-center gap-3 px-5 py-3 ${m.active ? "" : "opacity-60"}`}>
                  <Avatar text={initials(m.display_name)} size="sm" />
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                      {m.display_name}
                      {m.bookable && (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-700">
                          Bookable
                        </span>
                      )}
                      {!m.active && (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-500">
                          Disabled
                        </span>
                      )}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {[ROLE_LABELS[m.role] ?? m.role, m.job_title, m.specialty].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <span className="text-xs tabular-nums text-slate-400">
                    {m.registration_number ? `Reg. ${m.registration_number}` : "No registration no."}
                  </span>
                  {canManage && (
                    <button
                      onClick={() => setEditing(m)}
                      className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      Edit
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        ))
      )}
    </main>
  );
}
