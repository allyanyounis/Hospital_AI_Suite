/**
 * Patients feature: the hospital's patient registry (/patients): search, register, edit. Other features pick a
 * patient with `PatientPicker` (e.g. booking an appointment).
 * Public API of the module: import from "@/features/patients", never from its internal files.
 */

export { PatientsView } from "./views/PatientsView";
export { PatientPicker } from "./components/PatientPicker";
export { patientsApi } from "./api";
export { SEXES } from "./types";
export type * from "./types";
