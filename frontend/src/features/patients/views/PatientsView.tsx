"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useSession } from "@/features/auth";
import { formatDate } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { patientsApi } from "../api";
import { PatientRecordForm } from "../components/PatientRecordForm";
import type { PatientRecord } from "../types";

/** The hospital's patient registry: one record per person, searchable by name, MRN or phone. */
export function PatientsView() {
  // useSearchParams needs a Suspense boundary so the page can still be prerendered
  return (
    <Suspense
      fallback={
        <main className="flex justify-center p-16">
          <Spinner className="h-6 w-6" />
        </main>
      }
    >
      <Registry />
    </Suspense>
  );
}

function Registry() {
  const canManage = useSession().can("patients.manage");
  const initialQuery = useSearchParams().get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [patients, setPatients] = useState<PatientRecord[] | null>(null);
  const [editing, setEditing] = useState<PatientRecord | null>(null);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      patientsApi
        .search(query)
        .then(setPatients)
        .catch((e) => {
          setPatients([]);
          setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not load patients" });
        });
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const upsert = (p: PatientRecord) => setPatients((list) => [p, ...(list ?? []).filter((x) => x.id !== p.id)]);

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Contact className="h-6 w-6" />}
        title="Patient registry"
        subtitle="Every patient once, shared by the front desk, appointments, the AI scribe and the patient portal."
        aside={
          <div className="flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:w-80">
            <Icons.Search className="h-4 w-4 shrink-0 text-slate-400" />
            <input
              id="patient-search"
              aria-label="Search patients"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Name, MRN or phone…"
              className="w-full bg-transparent text-sm text-slate-700 outline-none"
            />
          </div>
        }
      />
      {notice && <Notice tone={notice.ok ? "success" : "error"}>{notice.text}</Notice>}

      <div className={`grid items-start gap-5 ${canManage ? "xl:grid-cols-[minmax(0,1fr)_360px]" : ""}`}>
        <Card className="overflow-hidden">
          {patients === null ? (
            <div className="flex justify-center py-12">
              <Spinner className="h-6 w-6" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-2.5">Patient</th>
                    <th className="px-3 py-2.5">MRN</th>
                    <th className="px-3 py-2.5">Date of birth</th>
                    <th className="px-3 py-2.5">Phone</th>
                    <th className="px-3 py-2.5">Portal</th>
                    {canManage && <th className="px-5 py-2.5" />}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {patients.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                        {query.trim() ? `No patients match "${query.trim()}".` : "No patients registered yet."}
                      </td>
                    </tr>
                  ) : (
                    patients.map((p) => (
                      <tr key={p.id} className="hover:bg-brand-50/40">
                        <td className="px-5 py-3">
                          <Link
                            href={`/patients/${p.id}`}
                            className="font-semibold text-slate-900 hover:text-brand-700 hover:underline"
                          >
                            {p.full_name}
                          </Link>
                          <p className="text-xs text-slate-400">
                            {[p.sex, p.email].filter(Boolean).join(" · ") || `ID #${p.id}`}
                          </p>
                        </td>
                        <td className="px-3 py-3 font-mono text-xs text-slate-700">{p.mrn || "—"}</td>
                        <td className="px-3 py-3 text-slate-600">
                          {p.date_of_birth ? formatDate(new Date(`${p.date_of_birth}T00:00:00`)) : "—"}
                        </td>
                        <td className="px-3 py-3 tabular-nums text-slate-600">{p.phone || "—"}</td>
                        <td className="px-3 py-3">
                          {p.has_account ? (
                            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                              Account
                            </span>
                          ) : (
                            <span className="text-xs text-slate-300">None</span>
                          )}
                        </td>
                        {canManage && (
                          <td className="px-5 py-3 text-right">
                            <button
                              onClick={() => setEditing(p)}
                              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                            >
                              Edit
                            </button>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {canManage && (
          <Card className="p-5">
            <p className="text-sm font-semibold text-slate-900">
              {editing ? `Edit · ${editing.full_name}` : "Register a patient"}
            </p>
            <p className="mb-4 text-xs text-slate-500">
              {editing
                ? "Changes apply everywhere this patient appears."
                : "Check the search first so nobody is registered twice."}
            </p>
            <PatientRecordForm
              key={editing?.id ?? "new"}
              current={editing ?? undefined}
              onCancel={editing ? () => setEditing(null) : undefined}
              onSaved={(p) => {
                upsert(p);
                setNotice({ ok: true, text: `${editing ? "Saved" : "Registered"} ${p.full_name}.` });
                setEditing(null);
              }}
            />
          </Card>
        )}
      </div>
    </main>
  );
}
