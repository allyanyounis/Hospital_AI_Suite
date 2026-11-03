"use client";

/** The scribe's cards on the dashboard home page. */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icons } from "@/components/icons";
import { Avatar, Card, Spinner, StatCard, StatusPill } from "@/components/ui";
import { api, type EncounterSummary, type Sample } from "@/lib/api";
import { formatDateTime, initials, isToday } from "@/lib/format";

/** The signed-in clinician's encounters; null while loading. */
export function useEncounters(): EncounterSummary[] | null {
  const [encounters, setEncounters] = useState<EncounterSummary[] | null>(null);
  useEffect(() => {
    api
      .encounters()
      .then(setEncounters)
      .catch(() => setEncounters([]));
  }, []);
  return encounters;
}

export function ScribeStats({ encounters }: { encounters: EncounterSummary[] }) {
  const toReview = encounters.filter((e) => e.status === "ready").length;
  const drafting = encounters.filter((e) => e.status === "drafting").length;
  const signedToday = encounters.filter((e) => e.approved_at && isToday(e.approved_at)).length;
  return (
    <>
      <StatCard
        icon={<Icons.File />}
        label="Notes to review"
        value={toReview}
        note={drafting ? `${drafting} drafting now` : "Scribe pipeline"}
        accent={toReview > 0}
      />
      <StatCard icon={<Icons.CheckCircle />} label="Notes signed today" value={signedToday} />
    </>
  );
}

export function RecentEncountersCard({ encounters }: { encounters: EncounterSummary[] | null }) {
  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <p className="text-sm font-semibold text-slate-900">Recent encounters</p>
          <p className="text-xs text-slate-500">Your latest scribe sessions and where each note stands</p>
        </div>
        <Link href="/scribe/board" className="flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
          Open board <Icons.ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      {encounters === null ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : encounters.length === 0 ? (
        <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-700">
            <Icons.Mic />
          </span>
          <p className="text-sm font-semibold text-slate-800">No encounters yet</p>
          <p className="text-sm text-slate-500">Start a live session, or open an example consultation.</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {encounters.slice(0, 5).map((e) => (
            <li key={e.id}>
              <Link href={`/scribe/encounters?id=${e.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-brand-50/40">
                <Avatar text={initials(e.patient.name)} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900">{e.patient.name || "Unnamed patient"}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(e.created_at)}</p>
                </div>
                <StatusPill status={e.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Example consultations; opening one starts a scribe session. Hidden when there are none. */
export function SampleConsultationsCard({ onError }: { onError: (message: string | null) => void }) {
  const router = useRouter();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busySample, setBusySample] = useState<string | null>(null);

  useEffect(() => {
    api
      .samples()
      .then(setSamples)
      .catch(() => {});
  }, []);

  async function openSample(id: string) {
    setBusySample(id);
    onError(null);
    try {
      const e = await api.startFromSample(id);
      router.push(`/scribe/session?encounter=${e.id}`);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not load the sample");
      setBusySample(null);
    }
  }

  if (samples.length === 0) return null;
  return (
    <Card className="p-5">
      <div className="mb-3 flex items-start gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
          <Icons.Book />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-900">Example consultations</p>
          <p className="text-xs text-slate-500">Synthetic cardiology transcripts to try the scribe without recording.</p>
        </div>
      </div>
      <ul className="grid gap-1.5 sm:grid-cols-2">
        {samples.map((s) => (
          <li key={s.id}>
            <button
              onClick={() => openSample(s.id)}
              disabled={busySample !== null}
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-left text-sm text-slate-700 hover:border-brand-200 hover:bg-brand-50/50 disabled:opacity-50"
            >
              <span className="truncate">{s.title}</span>
              {busySample === s.id ? (
                <Spinner className="h-3.5 w-3.5" />
              ) : (
                <Icons.ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              )}
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function MicrophoneTipCard() {
  return (
    <Card className="flex gap-3 border-amber-200 bg-amber-50/60 p-5">
      <Icons.Mic className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
      <div>
        <p className="text-sm font-semibold text-slate-900">Tip: microphone position</p>
        <p className="text-xs leading-relaxed text-slate-600">
          Place the device between you and the patient. Clear speech from both sides gives the best speaker separation and more
          accurate medical terms.
        </p>
      </div>
    </Card>
  );
}
