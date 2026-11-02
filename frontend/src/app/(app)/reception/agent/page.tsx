"use client";

import { useCallback, useEffect, useState } from "react";
import { Icons } from "@/components/icons";
import { VoiceAgent } from "@/components/reception/VoiceAgent";
import { PageHeader, StatCard } from "@/components/ui";
import { api, type ClinicSchedule } from "@/lib/api";
import { isUpcoming } from "@/lib/appointments";
import { isToday } from "@/lib/format";
import { useAppointments } from "@/lib/hooks";
import { weekdayIndex } from "@/lib/schedule";
import type { CallStatus } from "@/lib/useVapiCall";

const STATUS: Record<CallStatus, { label: string; note: string }> = {
  idle: { label: "Ready", note: "Waiting for a call" },
  connecting: { label: "Connecting", note: "Starting the call" },
  active: { label: "On a call", note: "Talking to a patient" },
};

export default function VoiceAgentPage() {
  const { appointments } = useAppointments(); // refreshes live when the agent books or cancels
  const [schedule, setSchedule] = useState<ClinicSchedule | null>(null);
  const [status, setStatus] = useState<CallStatus>("idle");
  const onStatusChange = useCallback((s: CallStatus) => setStatus(s), []);

  useEffect(() => {
    api
      .schedule()
      .then(setSchedule)
      .catch(() => {});
  }, []);

  const list = appointments ?? [];
  const today = schedule?.days[weekdayIndex()];

  return (
    <main className="px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Bot className="h-6 w-6" />}
        title="AI Voice Receptionist"
        subtitle="Talk to the voice agent that books, checks and cancels appointments within the clinic schedule."
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
          icon={<Icons.Clock />}
          label="Today's hours"
          value={!today ? "—" : today.enabled ? `${today.start}–${today.end}` : "Day off"}
          note={schedule ? `${schedule.slot_minutes}-minute slots` : undefined}
        />
      </div>

      <VoiceAgent onStatusChange={onStatusChange} />
    </main>
  );
}
