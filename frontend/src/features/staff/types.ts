/** Staff directory data contracts (FastAPI /api/staff). A profile belongs to a staff account, never a patient. */

import type { Role } from "@/features/auth";

export type StaffMember = {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  active: boolean;
  department: { id: number; code: string; name: string };
  job_title: string;
  specialty: string;
  registration_number: string;
  /** Patients can book outpatient (OPD) appointments with this member; has an OPD schedule */
  bookable: boolean;
};

/** Strings may be "" (stored as empty) */
export type StaffProfileInput = {
  department_id: number;
  job_title: string;
  specialty: string;
  registration_number: string;
  bookable: boolean;
};

export type StaffFilter = { department_id?: number; bookable?: boolean };
