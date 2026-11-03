"use client";

import { useEffect, useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { departmentsApi } from "../api";
import { NewDepartmentForm } from "../components/NewDepartmentForm";
import { DEPARTMENT_KINDS, type Department, type DepartmentKind } from "../types";

const field =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const kindLabel = (kind: DepartmentKind) => DEPARTMENT_KINDS.find((k) => k.value === kind)?.label ?? kind;
const smallButton =
  "rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50";

/** Admin: the hospital's departments. Departments are deactivated, never deleted, so history keeps its labels. */
export function DepartmentsView() {
  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const [editing, setEditing] = useState<number | null>(null);

  useEffect(() => {
    departmentsApi
      .list()
      .then(setDepartments)
      .catch((e) => {
        setDepartments([]);
        setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load departments" });
      });
  }, []);

  const upsert = (d: Department) =>
    setDepartments((list) => [...(list ?? []).filter((x) => x.id !== d.id), d].sort((a, b) => a.name.localeCompare(b.name)));

  async function run(action: () => Promise<Department>, done: string): Promise<boolean> {
    try {
      const d = await action();
      upsert(d);
      setNotice({ ok: true, text: `${done} ${d.name}.` });
      return true;
    } catch (e) {
      setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not save the department" });
      return false;
    }
  }

  const list = departments ?? [];

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Building className="h-6 w-6" />}
        title="Departments"
        subtitle="How the hospital is organised. Every staff member belongs to a department, and patients book doctors through their department."
      />
      {notice && <Notice tone={notice.ok ? "success" : "error"}>{notice.text}</Notice>}

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="overflow-hidden">
          {departments === null ? (
            <div className="flex justify-center py-12">
              <Spinner className="h-6 w-6" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-2.5">Code</th>
                    <th className="px-3 py-2.5">Name</th>
                    <th className="px-3 py-2.5">Kind</th>
                    <th className="px-3 py-2.5 text-right">Staff</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-5 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {list.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                        No departments yet. Add the first one on the right.
                      </td>
                    </tr>
                  ) : (
                    list.map((d) =>
                      editing === d.id ? (
                        <EditRow
                          key={d.id}
                          department={d}
                          onCancel={() => setEditing(null)}
                          onSave={async (change) => {
                            if (await run(() => departmentsApi.update(d.id, change), "Saved")) setEditing(null);
                          }}
                        />
                      ) : (
                        <tr key={d.id} className={d.active ? "" : "opacity-60"}>
                          <td className="px-5 py-3 font-mono text-xs font-semibold text-brand-700">{d.code}</td>
                          <td className="px-3 py-3 font-medium text-slate-900">{d.name}</td>
                          <td className="px-3 py-3 text-slate-600">{kindLabel(d.kind)}</td>
                          <td className="px-3 py-3 text-right tabular-nums text-slate-700">{d.staff_count}</td>
                          <td className="px-3 py-3">
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                d.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                              }`}
                            >
                              {d.active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-right">
                            <div className="flex justify-end gap-2">
                              <button onClick={() => setEditing(d.id)} className={smallButton}>
                                Edit
                              </button>
                              <button
                                onClick={() =>
                                  run(
                                    () => departmentsApi.update(d.id, { active: !d.active }),
                                    d.active ? "Deactivated" : "Activated",
                                  )
                                }
                                className={smallButton}
                              >
                                {d.active ? "Deactivate" : "Activate"}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ),
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <NewDepartmentForm onCreate={(input) => run(() => departmentsApi.create(input), "Created")} />
      </div>
    </main>
  );
}

function EditRow({
  department,
  onSave,
  onCancel,
}: {
  department: Department;
  onSave: (change: { name: string; kind: DepartmentKind }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(department.name);
  const [kind, setKind] = useState(department.kind);
  return (
    <tr className="bg-brand-50/40">
      <td className="px-5 py-3 font-mono text-xs font-semibold text-brand-700">{department.code}</td>
      <td className="px-3 py-2">
        <input
          id={`department-name-${department.id}`}
          aria-label="Department name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={120}
          className={field}
        />
      </td>
      <td className="px-3 py-2">
        <select
          id={`department-kind-${department.id}`}
          aria-label="Kind"
          value={kind}
          onChange={(e) => setKind(e.target.value as DepartmentKind)}
          className={field}
        >
          {DEPARTMENT_KINDS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-3 text-right tabular-nums text-slate-700">{department.staff_count}</td>
      <td />
      <td className="px-5 py-3 text-right">
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className={smallButton}>
            Cancel
          </button>
          <button
            onClick={() => onSave({ name: name.trim(), kind })}
            disabled={!name.trim()}
            className="rounded-lg bg-brand-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-brand-800 disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </td>
    </tr>
  );
}
