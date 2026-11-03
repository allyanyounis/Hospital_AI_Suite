"use client";

import { Bot, User } from "lucide-react";
import { formatClockTime, formatDate } from "@/shared/lib/format";
import { Modal } from "@/shared/ui/overlays";
import { parseCallTranscript } from "../helpers";
import type { Appointment } from "../types";

/** The voice call that booked an appointment, shown as a chat. */
export function CallTranscriptModal({ appointment, onClose }: { appointment: Appointment; onClose: () => void }) {
  const start = new Date(appointment.start_time);
  const turns = parseCallTranscript(appointment.transcript ?? "");

  return (
    <Modal
      title="Call transcript"
      subtitle={
        <>
          {appointment.patient_name} · {formatDate(start)} at {formatClockTime(start)} ·{" "}
          {appointment.reason || "General Consultation"}
        </>
      }
      onClose={onClose}
      footer={
        <div className="flex justify-between text-xs text-slate-400">
          <span>AI receptionist on the left · patient on the right</span>
          <span>{turns.length} messages</span>
        </div>
      }
    >
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
    </Modal>
  );
}
