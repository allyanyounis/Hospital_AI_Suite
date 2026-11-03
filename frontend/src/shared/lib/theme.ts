/**
 * Hex values for places that can't read CSS variables (Recharts / SVG attributes).
 * Keep in sync with the --color-* tokens in src/app/globals.css.
 */
export const CHART = {
  primary: "#8b2635", // brand-700
  primaryDark: "#6b1925", // brand-800
  primarySoft: "#fde8e9", // brand-100
  accent: "#f59e0b", // amber-500: closed days, highlights
  grid: "#eef0f3",
  axis: "#6b7280",
  track: "#e2e8f0",
  /** Theatre case phases; keep in sync with --color-phase-* */
  phases: {
    anaes: "#f0a3ad", // brand-300
    prep: "#e2e8f0", // slate-200
    surgery: "#8b2635", // brand-700
  },
  risk: "#e11d48", // rose-600, --color-risk
  closeLine: "#f43f5e", // rose-500, --color-close-line
  /** Normal-range band behind vitals sparklines */
  band: "#d1fae5", // emerald-100
} as const;
