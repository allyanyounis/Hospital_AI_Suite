"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSession } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";
import { Card, Notice, PageHeader, Spinner, StatCard, Tabs } from "@/shared/ui/ui";
import { theatreApi, theatreKeys } from "../api";
import { ActionNeeded } from "../components/board/ActionNeeded";
import { CaseDrawer } from "../components/board/CaseDrawer";
import { CaseTable } from "../components/board/CaseTable";
import { DemoClock } from "../components/board/DemoClock";
import { LaterTable, WaitingTable } from "../components/board/OffList";
import { RoomChips } from "../components/board/RoomChips";
import { Timeline } from "../components/board/Timeline";
import { IntakeModal } from "../components/IntakeModal";
import { useDemoClock } from "../lib/demoClock";
import { addDays, dayLabel, hm, weekday } from "../lib/time";
import type { Board } from "../types";

type Tab = "lists" | "action" | "waiting" | "later";

/** Case ids the planner suggests moving off today (room tips and urgent-case proposals). */
function markedCases(board: Board): Set<number> {
  const ids = new Set<number>();
  for (const r of board.rooms) {
    if (r.suggestion) ids.add(r.suggestion.case);
    if (r.nudge) ids.add(r.nudge.case);
  }
  for (const p of board.proposals ?? []) if (p.move) ids.add(p.move.case);
  return ids;
}

/**
 * The theatre board (/theatre): one day's lists across every theatre. KPIs and room chips on top; the detail sits
 * in tabs (lists, decisions, waiting list, moved later) so the page never shows everything at once. Refreshes on
 * every theatre change (live event) and once a minute for today's clock.
 */
export function BoardView() {
  const session = useSession();
  const canManage = session.can("theatre.manage");
  const isAdmin = session.user?.role === "admin";
  const at = useDemoClock();
  const [day, setDay] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("lists");
  const [room, setRoom] = useState<number | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [intake, setIntake] = useState<{ caseId: number | null } | null>(null);

  const q = useQuery({
    queryKey: theatreKeys.board(day, at),
    queryFn: () => theatreApi.board(day, at),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (at == null && query.state.data?.day === query.state.data?.today ? 60_000 : false),
  });
  const board = q.data;
  const marked = useMemo(() => (board ? markedCases(board) : new Set<number>()), [board]);

  if (q.isPending)
    return (
      <main className="flex justify-center p-16">
        <Spinner className="h-6 w-6" />
      </main>
    );
  if (q.isError || !board)
    return (
      <main className="px-4 py-6 sm:px-8">
        <Notice tone="error">{q.error?.message ?? "Could not load the board"}</Notice>
      </main>
    );

  const isToday = board.day === board.today;
  const shown: Tab = tab === "action" && !isToday ? "lists" : tab;
  const rooms = room == null ? board.rooms : board.rooms.filter((r) => r.id === room);
  const cases = board.rooms.flatMap((r) => r.cases);
  const late = board.rooms.filter((r) => r.cases.length && r.forecast.over_pct >= 50).length;
  const decisions =
    (board.proposals?.length ?? 0) + board.rooms.filter((r) => r.suggestion || r.nudge).length;
  const go = (step: 1 | -1) => setDay(weekday(addDays(board.day, step), step));

  return (
    <main className="space-y-5 px-4 py-6 sm:px-8">
      <PageHeader
        icon={<Icons.Scissors className="h-6 w-6" />}
        title={
          <span className="flex items-center gap-2">
            <button onClick={() => go(-1)} aria-label="Previous day" className="rounded-lg p-1 text-slate-500 hover:bg-slate-100">
              <Icons.ChevronLeft className="h-5 w-5" />
            </button>
            {isToday ? "Today, " : ""}
            {dayLabel(board.day, { weekday: "long", day: "numeric", month: "long" })}
            <button onClick={() => go(1)} aria-label="Next day" className="rounded-lg p-1 text-slate-500 hover:bg-slate-100">
              <Icons.ChevronRight className="h-5 w-5" />
            </button>
            {!isToday && (
              <button onClick={() => setDay(null)} className="text-sm font-semibold text-brand-700 hover:underline">
                Back to today
              </button>
            )}
            {q.isFetching && <Spinner className="h-4 w-4" />}
          </span>
        }
        subtitle={isToday ? `Lists as of ${hm(board.now)}${at != null ? " (demo clock)" : ""}` : "Planned lists"}
        aside={
          <div className="flex flex-wrap items-center gap-2">
            {isAdmin && <DemoClock />}
            {canManage && isToday && (
              <button
                onClick={() => setIntake({ caseId: null })}
                className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-700"
              >
                <Icons.Siren className="h-4 w-4" /> Add emergency
              </button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          icon={<Icons.Clipboard className="h-5 w-5" />}
          label="Cases"
          value={cases.length}
          note={isToday ? `${cases.filter((c) => c.state === "done").length} done · ${cases.filter((c) => c.state === "in").length} in theatre` : `${board.rooms.filter((r) => r.cases.length).length} theatres in use`}
        />
        <StatCard
          icon={<Icons.Clock className="h-5 w-5" />}
          label="Likely past 16:00"
          value={`${late} of ${board.rooms.filter((r) => r.cases.length).length}`}
          note="theatres, ≥ 50% chance"
          accent={late > 0}
        />
        <StatCard
          icon={<Icons.Siren className="h-5 w-5" />}
          label="Urgent waiting"
          value={board.urgent_waiting}
          note={`${board.waiting} on the waiting list`}
          accent={board.urgent_waiting > 0}
        />
        <StatCard icon={<Icons.Calendar className="h-5 w-5" />} label="Moved to later" value={board.later} note="kept off an overrunning list" />
      </div>

      <RoomChips rooms={board.rooms} selected={room} onSelect={setRoom} />

      <Card className="overflow-hidden">
        <Tabs<Tab>
          value={shown}
          onChange={setTab}
          tabs={[
            { id: "lists", label: "Theatre lists" },
            { id: "action", label: "Action needed", count: isToday ? decisions : 0, disabled: !isToday },
            { id: "waiting", label: `Waiting list (${board.waiting})` },
            { id: "later", label: `Moved to later (${board.later})` },
          ]}
        />
        {shown === "lists" && (
          <>
            <Timeline board={board} rooms={rooms} marked={marked} onOpen={(c) => setOpen(c.id)} />
            <CaseTable rooms={rooms} marked={marked} onOpen={(c) => setOpen(c.id)} />
          </>
        )}
        {shown === "action" && <ActionNeeded board={board} canManage={canManage} onOpen={(c) => setOpen(c.id)} />}
        {shown === "waiting" && (
          <WaitingTable canManage={canManage} onIntake={(id) => setIntake({ caseId: id })} onOpen={setOpen} />
        )}
        {shown === "later" && <LaterTable onOpen={setOpen} />}
      </Card>

      {open != null && (
        <CaseDrawer
          caseId={open}
          canManage={canManage}
          onClose={() => setOpen(null)}
          onIntake={(id) => {
            setOpen(null);
            setIntake({ caseId: id });
          }}
        />
      )}
      {intake && <IntakeModal caseId={intake.caseId} onClose={() => setIntake(null)} />}
    </main>
  );
}
