"use client";

import { Bot, User, X } from "lucide-react";
import { useEffect } from "react";
import type { Appointment } from "@/lib/api";
import { parseCallTranscript } from "@/lib/appointments";
import { formatClockTime, formatDate } from "@/lib/format";

/** The voice call that booked an appointment, shown as a chat. */
export function CallTranscriptModal({ appointment, onClose }: { appointment: Appointment; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const start = new Date(appointment.start_time);
  const turns = parseCallTranscript(appointment.transcript ?? "");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Call transcript"
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-800">Call transcript</h3>
            <p className="text-sm text-slate-500">
              {appointment.patient_name} · {formatDate(start)} at {formatClockTime(start)} ·{" "}
              {appointment.reason || "General Consultation"}
            </p>
          </div>
          <button onClick={onClose} title="Close" className="p-1 text-slate-400 hover:text-slate-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-6 py-4 text-sm">
          {turns.map((turn, i) => (
            <div key={i} className={`flex gap-2 ${turn.role === "user" ? "justify-end" : "justify-start"}`}>
              {turn.role === "ai" && <Bot className="mt-1 h-4 w-4 shrink-0 text-brand-700" />}
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 ${
                  turn.role === "user"
                    ? "rounded-br-none bg-brand-700 text-white"
                    : "rounded-bl-none border border-slate-200 bg-white text-slate-800 shadow-sm"
                }`}
              >
                {turn.text}
              </div>
              {turn.role === "user" && <User className="mt-1 h-4 w-4 shrink-0 text-slate-400" />}
            </div>
          ))}
        </div>

        <div className="flex justify-between border-t border-slate-100 px-6 py-3 text-xs text-slate-400">
          <span>AI receptionist on the left · patient on the right</span>
          <span>{turns.length} messages</span>
        </div>
      </div>
    </div>
  );
}
