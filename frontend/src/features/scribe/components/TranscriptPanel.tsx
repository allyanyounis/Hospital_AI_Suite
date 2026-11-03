"use client";

import { useEffect, useRef } from "react";
import { formatDuration as formatTime } from "@/shared/lib/format";
import type { Transcript } from "../types";

export function TranscriptPanel({
  transcript,
  clinicianSpeaker,
  onSwapSpeakers,
  highlighted,
}: {
  transcript: Transcript;
  clinicianSpeaker: number;
  onSwapSpeakers?: () => void;
  highlighted: Set<number>;
}) {
  const refs = useRef(new Map<number, HTMLLIElement>());
  const speakers = [...new Set(transcript.segments.map((s) => s.speaker))];

  // Bring the first cited segment into view when a note statement is selected
  useEffect(() => {
    const first = Math.min(...highlighted);
    refs.current.get(first)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [highlighted]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          {transcript.segments.length} segments
          {transcript.duration ? ` · ${formatTime(transcript.duration)}` : ""} · {transcript.provider}
        </p>
        {speakers.length > 1 && onSwapSpeakers && (
          <button onClick={onSwapSpeakers} className="text-xs font-medium text-brand-700 hover:underline">
            Swap clinician / patient
          </button>
        )}
      </div>
      <ol className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {transcript.segments.map((s) => {
          const isClinician = s.speaker === clinicianSpeaker;
          const isHighlighted = highlighted.has(s.id);
          return (
            <li
              key={s.id}
              ref={(el) => {
                if (el) refs.current.set(s.id, el);
                else refs.current.delete(s.id);
              }}
              className="flex gap-3"
            >
              <span
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border bg-white text-xs font-bold ${
                  isClinician ? "border-brand-200 text-brand-700" : "border-slate-300 text-slate-600"
                }`}
              >
                {isClinician ? "C" : "P"}
              </span>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">{isClinician ? "Clinician" : "Patient"}</span>
                  <span className="tabular-nums text-slate-400">{formatTime(s.start)}</span>
                </div>
                <p
                  className={`rounded-xl border px-4 py-2.5 text-sm leading-relaxed text-slate-800 shadow-sm transition-colors ${
                    isHighlighted ? "border-amber-400 bg-amber-50 ring-2 ring-amber-200" : "border-slate-200 bg-white"
                  }`}
                >
                  {s.text}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
