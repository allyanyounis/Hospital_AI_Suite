"use client";

import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { type PatientRecord, PatientPicker } from "@/features/patients";
import type { StaffMember } from "@/features/staff";
import { toDateKey } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, Spinner } from "@/shared/ui/ui";
import { appointmentsApi } from "../api";
import type { Appointment } from "../types";

const field =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-700/20";
const labelClass = "block text-xs font-semibold text-slate-600";

/**
 * Front-desk booking: patient → doctor → date → a free slot. The server applies the same rules as the voice
 * agent (OPD hours, breaks, closed dates, one patient per slot), so a refused booking explains why.
 */
export function NewAppointmentForm({
  doctors,
  onBooked,
  onClose,
}: {
  doctors: StaffMember[];
  onBooked: (appointment: Appointment) => void;
  onClose: () => void;
}) {
  const [patient, setPatient] = useState<PatientRecord | null>(null);
  const [doctorId, setDoctorId] = useState<number>(doctors[0]?.id ?? 0);
  const [date, setDate] = useState(toDateKey(new Date()));
  const [slots, setSlots] = useState<string[] | null>(null);
  const [slot, setSlot] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!doctorId || !date) return;
    let current = true;
    appointmentsApi
      .availability(doctorId, date)
      .then((a) => current && setSlots(a.slots))
      .catch(() => current && setSlots([]));
    return () => {
      current = false;
    };
  }, [doctorId, date]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!patient || !slot) return;
    setBusy(true);
    setError(null);
    try {
      onBooked(
        await appointmentsApi.book({
          patient_id: patient.id,
          practitioner_id: doctorId,
          start_time: `${date}T${slot}`,
          reason: reason.trim(),
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not book the appointment");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mb-6 p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">New appointment</p>
          <p className="text-xs text-slate-500">Book a registered patient with a doctor in one of their free OPD slots.</p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close"
          className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {error && (
        <div className="mb-4">
          <Notice tone="error">{error}</Notice>
        </div>
      )}
      {doctors.length === 0 ? (
        <Notice tone="warning">No bookable doctors. Mark a doctor as bookable in Hospital → Staff first.</Notice>
      ) : (
        <form onSubmit={submit} className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className={labelClass} htmlFor="booking-patient">
              Patient
            </label>
            <PatientPicker id="booking-patient" value={patient} onChange={setPatient} />
          </div>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={labelClass} htmlFor="booking-doctor">
                Doctor
                <select
                  id="booking-doctor"
                  value={doctorId}
                  onChange={(e) => {
                    setDoctorId(Number(e.target.value));
                    setSlots(null);
                    setSlot("");
                  }}
                  className={field}
                >
                  {doctors.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.display_name} · {d.department.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className={labelClass} htmlFor="booking-date">
                Date
                <input
                  id="booking-date"
                  type="date"
                  value={date}
                  min={toDateKey(new Date())}
                  onChange={(e) => {
                    setDate(e.target.value);
                    setSlots(null);
                    setSlot("");
                  }}
                  className={field}
                />
              </label>
            </div>
            <div>
              <p className={labelClass}>Free slots</p>
              {slots === null ? (
                <Spinner className="mt-2 h-4 w-4" />
              ) : slots.length === 0 ? (
                <p className="mt-1 text-xs text-slate-400">No free slots on this date. Try another day or doctor.</p>
              ) : (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {slots.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setSlot(s)}
                      className={`rounded-lg border px-2.5 py-1 text-xs font-semibold tabular-nums ${
                        slot === s
                          ? "border-brand-700 bg-brand-700 text-white"
                          : "border-slate-200 bg-white text-slate-700 hover:border-brand-300 hover:bg-brand-50"
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <label className={labelClass} htmlFor="booking-reason">
              Reason
              <input
                id="booking-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Follow-up visit"
                maxLength={255}
                className={field}
              />
            </label>
            <button
              disabled={busy || !patient || !slot}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-700 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:opacity-50"
            >
              {busy ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : <Icons.Check />}
              Book appointment
            </button>
          </div>
        </form>
      )}
    </Card>
  );
}
