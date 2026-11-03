"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { Notice, PageHeader, Spinner } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { BookForm } from "../components/book/BookForm";
import { WeekCalendar } from "../components/book/WeekCalendar";

/** /theatre/book: the booking form beside a week × theatres calendar that shows where the operation fits. */
export function BookView() {
  const procedures = useQuery({ queryKey: theatreKeys.procedures(), queryFn: theatreApi.procedures });
  const surgeons = useQuery({ queryKey: theatreKeys.surgeons(), queryFn: theatreApi.surgeons });
  const [procedureCode, setProcedureCode] = useState("");
  const [surgeonId, setSurgeonId] = useState<number | null>(null);
  const [day, setDay] = useState<string | null>(null);
  const [start, setStart] = useState<string | null>(null);
  const procedure = procedures.data?.find((p) => p.code === procedureCode) ?? null;
  const error = procedures.error ?? surgeons.error;

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.CalendarClock className="h-6 w-6" />}
        title="Book an operation"
        subtitle="Choose the operation and the patient, then a day where it fits a rostered surgeon. Without a day the case joins the waiting list."
      />
      {error ? (
        <Notice tone="error">{error.message}</Notice>
      ) : !procedures.data || !surgeons.data ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6" />
        </div>
      ) : (
        <div className="grid items-start gap-5 xl:grid-cols-[24rem_minmax(0,1fr)]">
          <BookForm
            procedures={procedures.data}
            surgeons={surgeons.data}
            procedureCode={procedureCode}
            onProcedure={(code) => {
              setProcedureCode(code);
              setSurgeonId(null);
              setDay(null);
            }}
            surgeonId={surgeonId}
            onSurgeon={(id) => {
              setSurgeonId(id);
              setDay(null);
            }}
            day={day}
            onDay={setDay}
          />
          <WeekCalendar
            start={start}
            onStart={setStart}
            procedure={procedure}
            surgeonId={surgeonId}
            selectedDay={day}
            onPickDay={setDay}
          />
        </div>
      )}
    </main>
  );
}
