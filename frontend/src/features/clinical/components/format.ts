import type { BadgeTone } from "@/shared/ui/ui";
import type { LabFlag, VitalKey, VitalSigns } from "../types";

export const FLAG_TONE: Record<LabFlag, BadgeTone> = { low: "info", normal: "ok", high: "bad" };

/** Text classes for a value by its flag: in range stays slate, out of range is coloured. */
export const flagText = (flag: string | undefined) =>
  flag === "high" ? "text-rose-700 font-semibold" : flag === "low" ? "text-sky-700 font-semibold" : "text-slate-800";

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value == null) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(digits);
}

export function vitalValue(v: VitalSigns, key: VitalKey): string {
  if (key === "systolic_bp") return v.systolic_bp == null ? "—" : `${v.systolic_bp}/${v.diastolic_bp ?? "—"}`;
  return formatNumber(v[key]);
}

export const shortDateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

export const shortDate = (isoDate: string) =>
  new Date(isoDate.length === 10 ? `${isoDate}T00:00:00` : isoDate).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
