/** Account management data contracts (FastAPI /api/users, users.manage permission). */

import type { Role } from "@/features/auth";
import type { Sex } from "@/features/patients";

export type UserAccount = {
  username: string;
  display_name: string;
  role: Role;
  active: boolean;
  created_at: string;
  /** The patient record a patient account belongs to */
  patient: { id: number; name: string; mrn: string | null } | null;
};

export type NewAccount = {
  username: string;
  display_name: string;
  role: Role;
  password: string;
  /** Required when role is "patient"; display_name becomes the patient's name */
  patient?: { mrn: string; dob: string; sex: Sex };
};

/** Patient accounts can't become staff (or the reverse); create a new account instead. */
export type AccountChange = { display_name?: string; role?: Role; active?: boolean };
