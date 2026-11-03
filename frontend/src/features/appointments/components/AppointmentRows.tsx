import { Clock, MessageSquareText, Stethoscope, User } from "lucide-react";
import { dayOffset, formatClockTime, formatDate, relativeDay } from "@/shared/lib/format";
import { type Appointment, BOOKING_CHANNELS } from "../types";

export const NEW_BOOKING_MS = 86_400_000;
export const COLUMNS = 9;

export function statusOf(a: Appointment, now: Date) {
  const start = new Date(a.start_time);
  if (a.canceled) return { label: "Cancelled", className: "bg-rose-100 text-rose-600" };
  if (start < now) return { label: "Past", className: "bg-slate-100 text-slate-500" };
  if (dayOffset(start, now) === 0) return { label: "Today", className: "bg-amber-100 text-amber-800" };
  return { label: "Upcoming", className: "bg-brand-100 text-brand-800" };
}

export function AppointmentRow({
  appointment: a,
  index,
  now,
  onTranscript,
  onCancel,
}: {
  appointment: Appointment;
  index: number;
  now: Date;
  onTranscript: (a: Appointment) => void;
  /** Omit when the user may not cancel (no appointments.manage): the Cancel button is hidden */
  onCancel?: (a: Appointment) => void;
}) {
  const start = new Date(a.start_time);
  const created = new Date(a.created_at);
  const status = statusOf(a, now);
  const isNew = now.getTime() - created.getTime() < NEW_BOOKING_MS;
  const upcoming = !a.canceled && start >= now;

  return (
    <tr className={`group hover:bg-brand-50/60 ${a.canceled || start < now ? "opacity-60" : ""}`}>
      <td className="w-12 px-5 py-3.5 text-center font-medium text-slate-400">{index + 1}</td>
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
            <User className="h-4 w-4" />
          </span>
          <div>
            <p className="flex items-center gap-2 font-semibold text-slate-800">
              {a.patient_name}
              {isNew && (
                <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-700">New</span>
              )}
            </p>
            <p className="text-xs text-slate-400">ID #{a.id}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3.5">
        <p className="font-medium text-slate-800">{a.practitioner.display_name}</p>
        <p className="text-xs text-slate-400">{a.practitioner.department}</p>
      </td>
      <td className="px-4 py-3.5 text-slate-600">
        <p>{formatDate(start)}</p>
        <p className="text-xs text-slate-400">{relativeDay(start, now)}</p>
      </td>
      <td className="px-4 py-3.5 text-slate-600">
        <span className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400" />
          <span className={a.canceled ? "line-through" : ""}>{formatClockTime(start)}</span>
        </span>
      </td>
      <td className="px-4 py-3.5 text-slate-600">
        <span className="flex items-center gap-2">
          <Stethoscope className="h-4 w-4 text-slate-400" />
          {a.reason || "General Consultation"}
        </span>
      </td>
      <td className="px-4 py-3.5 text-xs text-slate-500">
        {formatDate(created)}, {formatClockTime(created)}
      </td>
      <td className="px-4 py-3.5">
        {a.transcript ? (
          <button
            onClick={() => onTranscript(a)}
            className="flex items-center gap-1.5 rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-200"
          >
            <MessageSquareText className="h-3.5 w-3.5" />
            View
          </button>
        ) : (
          <span className="text-xs text-slate-400">{BOOKING_CHANNELS[a.booked_via] ?? a.booked_via}</span>
        )}
      </td>
      <td className="px-5 py-3.5 text-right">
        <div className="flex items-center justify-end gap-2">
          {upcoming && onCancel && (
            <button
              onClick={() => onCancel(a)}
              className="rounded-full border border-rose-200 px-2.5 py-1 text-xs font-semibold text-rose-600 opacity-0 hover:bg-rose-50 focus:opacity-100 group-hover:opacity-100"
            >
              Cancel
            </button>
          )}
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status.className}`}>{status.label}</span>
        </div>
      </td>
    </tr>
  );
}

export function GroupRows({ heading, count, children }: { heading: string | null; count: number; children: React.ReactNode }) {
  return (
    <>
      {heading && (
        <tr className="bg-brand-50">
          <td colSpan={COLUMNS} className="px-5 py-2 text-xs font-semibold uppercase tracking-wide text-brand-700">
            {heading}
            <span className="ml-2 font-normal normal-case text-slate-400">
              {count} appointment{count === 1 ? "" : "s"}
            </span>
          </td>
        </tr>
      )}
      {children}
    </>
  );
}
