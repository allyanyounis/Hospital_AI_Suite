/** Session data contracts (FastAPI /api/login, /api/me, /api/config) and the route declarations every feature uses. */

import type { IconComponent } from "@/shared/ui/icons";

export type Role = "admin" | "doctor" | "nurse" | "receptionist" | "patient";

/** What a user may do. The server decides which roles get which permissions; the UI only reads the list. */
export type Permission =
  | "dashboard.view"
  | "scribe.use"
  | "clinical.view"
  | "theatre.view"
  | "theatre.manage"
  | "theatre.roster"
  | "theatre.insights"
  | "patients.view"
  | "patients.manage"
  | "appointments.view"
  | "appointments.manage"
  | "appointments.book"
  | "schedule.view"
  | "schedule.edit"
  | "staff.view"
  | "staff.manage"
  | "organization.manage"
  | "voice_agent.use"
  | "metrics.view_all"
  | "call_costs.view"
  | "users.manage"
  | "portal.use";

export type User = {
  username: string;
  display_name: string;
  role: Role;
  permissions: Permission[];
  /** The patient record a patient account belongs to; null for staff */
  patient_id: number | null;
};

/** Display labels only; access is always decided by permissions, never by role. */
export const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  doctor: "Doctor",
  nurse: "Nurse",
  receptionist: "Receptionist",
  patient: "Patient",
};

/** Staff roles in the order the Users page offers them */
export const STAFF_ROLES: Exclude<Role, "patient">[] = ["doctor", "nurse", "receptionist", "admin"];

export type AppConfig = {
  hospital_name: string;
  environment_banner: string;
  retention_days: number;
  hospital_timezone: string;
  transcriber: string;
  transcriber_ready: boolean;
  note_model: string;
  notes_ready: boolean;
};

/** Sidebar sections, top to bottom. A feature's nav entry names one of these. */
export const NAV_GROUPS = ["Overview", "Patients", "Clinical", "Theatres", "Front desk", "Hospital", "Me"] as const;
export type NavGroupName = (typeof NAV_GROUPS)[number];

/**
 * One page a feature serves. `path` is a prefix ("/" matches only the overview); the longest match decides the
 * permission (`null` = any signed-in user). Routes with `nav` get a sidebar link; `title` names pages without one.
 */
export type RouteDef = {
  path: string;
  permission: Permission | null;
  nav?: { group: NavGroupName; label: string; icon: IconComponent; order: number };
  title?: string;
};
