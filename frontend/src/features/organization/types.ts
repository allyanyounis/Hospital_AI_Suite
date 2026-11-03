/** Hospital organisation data contracts (FastAPI /api/departments). */

export type DepartmentKind = "clinical" | "diagnostic" | "support" | "administrative";

export const DEPARTMENT_KINDS: { value: DepartmentKind; label: string }[] = [
  { value: "clinical", label: "Clinical" },
  { value: "diagnostic", label: "Diagnostic" },
  { value: "support", label: "Support" },
  { value: "administrative", label: "Administrative" },
];

export type Department = {
  id: number;
  /** Short unique code, e.g. CARD */
  code: string;
  name: string;
  kind: DepartmentKind;
  /** Inactive departments keep their history but take no new staff */
  active: boolean;
  staff_count: number;
};

export type NewDepartment = { code: string; name: string; kind: DepartmentKind };
export type DepartmentChange = { name?: string; kind?: DepartmentKind; active?: boolean };
