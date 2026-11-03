export type Range = "week" | "month";

// Actual per-minute rates of the current VAPI assistant setup (USD)
export const RATES = [
  { name: "VAPI platform fee", provider: "VAPI", perMinute: 0.05 },
  { name: "Language model (LLM)", provider: "OpenAI GPT-4.1", perMinute: 0.02 },
  { name: "Text-to-speech (voice)", provider: "Elliot (VAPI Voice)", perMinute: 0.02 },
  { name: "Speech-to-text (transcriber)", provider: "Soniox / Deepgram", perMinute: 0.004 },
  { name: "Telephony / carrier", provider: "WebRTC browser audio", perMinute: 0 },
];
export const COST_PER_MINUTE = RATES.reduce((t, r) => t + r.perMinute, 0); // $0.094
export const PKR_PER_USD = 278; // ~25 PKR for $0.09

export interface Period {
  label: string;
  calls: number;
  minutes: number;
}

export const DATA: Record<Range, { periods: Period[]; previous: { calls: number; minutes: number }; caption: string }> = {
  week: {
    caption: "Last 7 days",
    periods: [
      { label: "Mon", calls: 18, minutes: 41.4 },
      { label: "Tue", calls: 22, minutes: 53.9 },
      { label: "Wed", calls: 15, minutes: 34.5 },
      { label: "Thu", calls: 26, minutes: 65.0 },
      { label: "Fri", calls: 20, minutes: 46.0 },
      { label: "Sat", calls: 9, minutes: 19.8 },
      { label: "Sun", calls: 3, minutes: 5.7 },
    ],
    previous: { calls: 101, minutes: 227.2 },
  },
  month: {
    caption: "Last 4 weeks",
    periods: [
      { label: "Week 1", calls: 94, minutes: 220.0 },
      { label: "Week 2", calls: 101, minutes: 227.2 },
      { label: "Week 3", calls: 117, minutes: 276.1 },
      { label: "Week 4", calls: 113, minutes: 266.3 },
    ],
    previous: { calls: 382, minutes: 889.5 },
  },
};

export const OUTCOMES = [
  { name: "Appointment booked", share: 0.46, className: "bg-brand-700" },
  { name: "Availability checked only", share: 0.27, className: "bg-brand-400" },
  { name: "Appointment cancelled", share: 0.11, className: "bg-amber-400" },
  { name: "Caller hung up / no action", share: 0.16, className: "bg-slate-300" },
];

export const RECENT_CALLS = [
  { time: "Today, 11:42 AM", caller: "Web call", seconds: 192, outcome: "Booked" },
  { time: "Today, 10:15 AM", caller: "Web call", seconds: 108, outcome: "Availability" },
  { time: "Today, 9:31 AM", caller: "Web call", seconds: 175, outcome: "Booked" },
  { time: "Yesterday, 4:20 PM", caller: "Web call", seconds: 34, outcome: "Hung up" },
  { time: "Yesterday, 2:05 PM", caller: "Web call", seconds: 130, outcome: "Cancelled" },
  { time: "Yesterday, 11:47 AM", caller: "Web call", seconds: 220, outcome: "Booked" },
];

export const OUTCOME_BADGE: Record<string, string> = {
  Booked: "bg-green-100 text-green-700",
  Availability: "bg-brand-100 text-brand-700",
  Cancelled: "bg-amber-100 text-amber-700",
  "Hung up": "bg-slate-100 text-slate-600",
};

export const usd = (n: number) => `$${n.toFixed(2)}`;
export const pkr = (n: number) => `Rs ${Math.round(n * PKR_PER_USD).toLocaleString()}`;
export const costOf = (minutes: number) => minutes * COST_PER_MINUTE;
export const formatCallDuration = (s: number) => `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
export const sum = (periods: Period[], key: "calls" | "minutes") => periods.reduce((t, p) => t + p[key], 0);
