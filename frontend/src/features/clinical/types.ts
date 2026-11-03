/** Clinical data contracts (FastAPI /api/clinical): a patient's labs, vitals, reports, history and allergies. */

export type LabFlag = "low" | "normal" | "high";
export type Trend = "" | "up" | "down" | "same";

export type LabTest = {
  id: number;
  code: string;
  name: string;
  unit: string;
  ref_low: number;
  ref_high: number;
  category: string;
};

/** The newest result of one test, with the one before it */
export type LabLatest = {
  test: string;
  name: string;
  unit: string;
  category: string;
  ref_low: number;
  ref_high: number;
  value: number;
  flag: LabFlag;
  collected_at: string;
  previous: number | null;
  previous_at: string | null;
  trend: Trend;
};

export type LabResult = {
  id: number;
  test: string;
  name: string;
  unit: string;
  value: number;
  flag: LabFlag;
  collected_at: string;
};

export type SeriesPoint = { at: string; value: number };

export type VitalKey = "heart_rate" | "systolic_bp" | "diastolic_bp" | "spo2" | "temperature_c" | "resp_rate";

export type VitalSigns = { id: number; recorded_at: string; flags: Partial<Record<VitalKey, "low" | "high">> } & Record<
  VitalKey,
  number | null
>;

export type VitalRange = { key: VitalKey; label: string; unit: string; low: number; high: number };

export const REPORT_KINDS = [
  "ultrasound",
  "ecg",
  "xray",
  "ct",
  "mri",
  "echo",
  "angiogram",
  "mammography",
  "pathology",
  "anaesthesia_review",
  "other",
] as const;
export type ReportKind = (typeof REPORT_KINDS)[number];

export const REPORT_LABEL: Record<ReportKind, string> = {
  ultrasound: "Ultrasound",
  ecg: "ECG",
  xray: "X-ray",
  ct: "CT",
  mri: "MRI",
  echo: "Echo",
  angiogram: "Angiogram",
  mammography: "Mammography",
  pathology: "Pathology",
  anaesthesia_review: "Anaesthesia review",
  other: "Other",
};

export type ReportListItem = {
  id: number;
  kind: ReportKind;
  title: string;
  /** YYYY-MM-DD */
  reported_on: string;
  author: string;
  excerpt: string;
};

export type Report = ReportListItem & { patient_id: number; body: string };

export type HistoryKind = "indication" | "condition" | "surgery";
export type HistoryEntry = { id: number; kind: HistoryKind; noted_on: string; text: string };

export type Allergy = { id: number; substance: string; reaction: string; severity: "mild" | "moderate" | "severe" | "unknown" };

export type ClinicalSummary = {
  patient_id: number;
  labs: LabLatest[];
  out_of_range: number;
  vitals: VitalSigns | null;
  previous_vitals: VitalSigns | null;
  vital_ranges: VitalRange[];
  allergies: Allergy[];
  report_counts: Partial<Record<ReportKind, number>>;
  history_count: number;
};
