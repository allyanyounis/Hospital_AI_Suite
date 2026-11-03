"use client";

import { useCallback, useEffect, useState } from "react";
import { isUpcoming, useAppointments } from "@/features/appointments";
import { type StaffMember, staffApi } from "@/features/staff";
import { isToday } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { PageHeader, StatCard } from "@/shared/ui/ui";
import { VoiceAgent } from "../components/VoiceAgent";
import type { CallStatus } from "../useVapiCall";

const STATUS: Record<CallStatus, { label: string; note: string }> = {
  idle: { label: "Ready", note: "Waiting for a call" },
  connecting: { label: "Connecting", note: "Starting the call" },
  active: { label: "On a call", note: "Talking to a patient" },
};

export function AgentView() {
  const { appointments } = useAppointments(); // refreshes live when the agent books or cancels
  const [doctors, setDoctors] = useState<StaffMember[] | null>(null);
  const [status, setStatus] = useState<CallStatus>("idle");
  const onStatusChange = useCallback((s: CallStatus) => setStatus(s), []);

  useEffect(() => {
    staffApi
      .doctors()
      .then(setDoctors)
      .catch(() => {});
  }, []);

  const list = appointments ?? [];

  return (
    <main className="px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Bot className="h-6 w-6" />}
        title="AI Voice Receptionist"
        subtitle="Talk to the voice agent that books, checks and cancels appointments within each doctor's OPD schedule."
      />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Icons.Phone />}
          label="Agent status"
          value={STATUS[status].label}
          note={STATUS[status].note}
          accent={status !== "idle"}
        />
        <StatCard icon={<Icons.Plus />} label="Booked today" value={list.filter((a) => isToday(a.created_at)).length} />
        <StatCard icon={<Icons.CalendarClock />} label="Upcoming appointments" value={list.filter((a) => isUpcoming(a)).length} />
        <StatCard
          icon={<Icons.UserCog />}
          label="Bookable doctors"
          value={doctors ? doctors.length : "—"}
          note={doctors && doctors.length > 1 ? "Callers choose a doctor or department" : undefined}
        />
      </div>

      <VoiceAgent onStatusChange={onStatusChange} />
    </main>
  );
}
