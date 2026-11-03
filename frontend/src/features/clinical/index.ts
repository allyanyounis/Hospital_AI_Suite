/**
 * Clinical feature: a patient's labs, vitals, reports, history and allergies. The chart page lives at
 * /patients/[id]; other features embed `ClinicalRecord` or `AllergyBanner`.
 * Public API of the module: import from "@/features/clinical", never from its internal files.
 */

export { PatientChartView } from "./views/PatientChartView";
export { ClinicalRecord } from "./components/ClinicalRecord";
export { AllergyBanner } from "./components/AllergyBanner";
export { clinicalApi, clinicalKeys } from "./api";
export { REPORT_KINDS, REPORT_LABEL } from "./types";
export type * from "./types";
