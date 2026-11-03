"use client";

import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { setDemoClock, useDemoClock } from "../../lib/demoClock";
import { hm } from "../../lib/time";

/** Admin-only: replay today at another time of day (the lists, forecasts and actions all use it). */
export function DemoClock() {
  const at = useDemoClock();
  const [draft, setDraft] = useState(at ?? 650);
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs ${
        at != null ? "border-amber-300 bg-amber-50 text-amber-900" : "border-slate-200 bg-white text-slate-600"
      }`}
    >
      <Icons.Clock className="h-3.5 w-3.5" />
      <span className="font-semibold">Demo clock</span>
      <input
        type="range"
        aria-label="Demo time"
        min={420}
        max={1140}
        step={5}
        value={draft}
        onChange={(e) => setDraft(Number(e.target.value))}
        onPointerUp={() => setDemoClock(draft)}
        onKeyUp={() => setDemoClock(draft)}
        className="w-28 accent-brand-700"
      />
      <span className="w-10 tabular-nums">{hm(at ?? draft)}</span>
      {at != null ? (
        <button onClick={() => setDemoClock(null)} className="font-semibold text-brand-700 hover:underline">
          Real time
        </button>
      ) : (
        <button onClick={() => setDemoClock(draft)} className="font-semibold text-brand-700 hover:underline">
          Use
        </button>
      )}
    </div>
  );
}
