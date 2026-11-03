"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSession } from "@/features/auth";
import { patientsApi } from "@/features/patients";
import { Icons } from "@/shared/ui/icons";
import { Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { ClinicalRecord } from "../components/ClinicalRecord";

function age(dob: string): number | null {
  if (!dob) return null;
  const birth = new Date(`${dob}T00:00:00`);
  const now = new Date();
  return now.getFullYear() - birth.getFullYear() - (now < new Date(now.getFullYear(), birth.getMonth(), birth.getDate()) ? 1 : 0);
}

/** One patient's chart (/patients/[id]): who they are, then their clinical record in tabs. */
export function PatientChartView({ patientId }: { patientId: number }) {
  const canView = useSession().can("clinical.view");
  const patient = useQuery({ queryKey: ["patients", patientId], queryFn: () => patientsApi.get(patientId) });
  const p = patient.data;
  const years = p ? age(p.date_of_birth) : null;

  return (
    <main className="space-y-4 px-4 py-6 sm:px-8">
      <Link href="/patients" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-700">
        <Icons.ArrowLeft className="h-4 w-4" /> Patient registry
      </Link>
      {patient.isPending ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : patient.isError ? (
        <Notice tone="error">{patient.error.message}</Notice>
      ) : (
        <>
          <PageHeader
            icon={<Icons.User className="h-6 w-6" />}
            title={p!.full_name}
            subtitle={[p!.mrn && `MRN ${p!.mrn}`, years != null && `${years} y`, p!.sex, p!.phone]
              .filter(Boolean)
              .join(" · ")}
          />
          {canView ? (
            <ClinicalRecord patientId={patientId} />
          ) : (
            <Notice>Clinical records are visible to nurses, doctors and administrators.</Notice>
          )}
        </>
      )}
    </main>
  );
}
