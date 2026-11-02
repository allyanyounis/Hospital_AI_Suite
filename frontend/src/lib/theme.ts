/**
 * Hex values for places that can't read CSS variables (Recharts / SVG attributes).
 * Keep in sync with the --color-brand-* tokens in src/app/globals.css.
 */
export const CHART = {
  primary: "#8b2635", // brand-700
  primaryDark: "#6b1925", // brand-800
  primarySoft: "#fde8e9", // brand-100
  accent: "#f59e0b", // amber-500: closed days, highlights
  grid: "#eef0f3",
  axis: "#6b7280",
  track: "#e2e8f0",
} as const;
