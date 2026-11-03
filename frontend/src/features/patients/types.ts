/** Patient registry data contracts (FastAPI /api/patients). One record per person, shared by every module. */

export type Sex = "" | "Female" | "Male" | "Other" | "Not stated";
export const SEXES: Exclude<Sex, "">[] = ["Female", "Male", "Other", "Not stated"];

/** Strings are "" when unknown */
export type PatientRecord = {
  id: number;
  /** Medical record number; unique when set */
  mrn: string;
  full_name: string;
  sex: Sex;
  /** YYYY-MM-DD or "" */
  date_of_birth: string;
  phone: string;
  email: string;
  created_at: string;
  /** Has a patient portal account */
  has_account: boolean;
};

export type PatientInput = {
  full_name: string;
  mrn: string;
  sex: Sex;
  date_of_birth: string;
  phone: string;
  email: string;
};

export const EMPTY_PATIENT_INPUT: PatientInput = { full_name: "", mrn: "", sex: "", date_of_birth: "", phone: "", email: "" };
