/** Patient portal data contracts (FastAPI /api/portal/*, portal.use permission). Only the signed-in patient's data. */

/** Strings are "" when unknown */
export type PortalProfile = { name: string; mrn: string; dob: string; sex: string };

export type PortalAppointment = {
  id: number;
  reason: string | null;
  start_time: string;
  canceled: boolean;
  created_at: string;
  /** The doctor's name and department */
  doctor: string;
  department: string;
};
