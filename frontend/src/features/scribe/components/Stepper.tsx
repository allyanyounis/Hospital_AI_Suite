import { Icons } from "@/shared/ui/icons";
import { Card } from "@/shared/ui/ui";

/** Live session steps: Setup -> Listening -> Synthesize. */
const STEPS = ["Setup", "Listening", "Synthesize"];

export function Stepper({ step }: { step: number }) {
  return (
    <Card className="mb-5 px-6 py-4">
      <ol className="flex items-start">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = n < step;
          const active = n === step;
          return (
            <li key={label} className={`flex items-start ${n < STEPS.length ? "flex-1" : ""}`}>
              <div className="flex flex-col items-center gap-1.5">
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-colors ${
                    done
                      ? "bg-brand-700 text-white"
                      : active
                        ? "bg-amber-400 text-brand-950 ring-4 ring-amber-100"
                        : "border-2 border-slate-200 bg-white text-slate-400"
                  }`}
                >
                  {done ? <Icons.Check className="h-4 w-4" /> : n}
                </span>
                <span
                  className={`text-[11px] font-bold uppercase tracking-wider ${done || active ? "text-brand-900" : "text-slate-400"}`}
                >
                  {label}
                </span>
              </div>
              {n < STEPS.length && (
                <span className={`mx-3 mt-5 h-0.5 flex-1 rounded-full ${n < step ? "bg-brand-600" : "bg-slate-200"}`} />
              )}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
