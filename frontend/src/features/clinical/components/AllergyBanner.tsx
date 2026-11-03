import { Icons } from "@/shared/ui/icons";
import type { Allergy } from "../types";

/** A loud strip listing the patient's allergies, or a quiet "no known allergies" line. */
export function AllergyBanner({ allergies }: { allergies: Allergy[] }) {
  if (!allergies.length)
    return (
      <p className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500">
        <Icons.CheckCircle className="h-4 w-4 text-emerald-600" /> No known allergies
      </p>
    );
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-800">
      <Icons.Alert className="h-4 w-4 shrink-0" />
      <span className="font-semibold">Allergies:</span>
      {allergies.map((a) => (
        <span
          key={a.id}
          title={[a.reaction, a.severity !== "unknown" ? a.severity : ""].filter(Boolean).join(" · ")}
          className="rounded-md border border-rose-200 bg-white px-2 py-0.5 text-xs font-semibold"
        >
          {a.substance}
          {a.severity === "severe" && <span className="ml-1 text-rose-600">· severe</span>}
        </span>
      ))}
    </div>
  );
}
