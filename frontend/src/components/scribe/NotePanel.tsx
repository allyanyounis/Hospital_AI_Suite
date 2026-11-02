"use client";

import { useState } from "react";
import type { Finding, Note } from "@/lib/api";
import { noteToText } from "@/lib/format";
import { ReviewPanel } from "./ReviewPanel";

type Position = { section: number; statement: number };

export function NotePanel({
  note,
  approved,
  onChange,
  onApprove,
  onSelect,
  findings,
  reviewing,
  onReview,
  onDismissFindings,
}: {
  note: Note;
  approved: boolean;
  onChange: (note: Note) => void;
  onApprove: () => Promise<boolean>;
  onSelect: (sourceIds: number[]) => void;
  findings: Finding[] | null;
  reviewing: boolean;
  onReview: () => void;
  onDismissFindings: () => void;
}) {
  const [active, setActive] = useState<Position | null>(null);
  const [copied, setCopied] = useState(false);

  function update(fn: (draft: Note) => void) {
    const draft: Note = structuredClone(note);
    fn(draft);
    onChange(draft);
  }

  function select(pos: Position | null) {
    setActive(pos);
    onSelect(pos ? note.sections[pos.section].statements[pos.statement].source_segment_ids : []);
  }

  async function approveAndCopy() {
    const high = findings?.filter((f) => f.severity === "high").length ?? 0;
    if (!approved && high && !confirm(`The safety check found ${high} high-severity issue(s). Approve anyway?`)) return;
    if (!approved && !(await onApprove())) return;
    await navigator.clipboard.writeText(noteToText(note));
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {findings && <ReviewPanel findings={findings} onSelect={onSelect} onDismiss={onDismissFindings} />}
        {note.sections.map((section, si) => (
          <section key={si}>
            <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">{section.heading}</h3>
            {section.statements.length === 0 && !approved && <p className="text-sm italic text-slate-400">Not discussed</p>}
            <ul className="space-y-1">
              {section.statements.map((st, i) => {
                const isActive = active?.section === si && active.statement === i;
                const unsourced = st.source_segment_ids.length === 0;
                return (
                  <li key={i} className="group flex items-start gap-2">
                    <span
                      className={`mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full ${unsourced ? "bg-slate-300" : "bg-amber-400"}`}
                      title={unsourced ? "Added or edited by clinician (no transcript source)" : "Linked to transcript"}
                    />
                    <textarea
                      value={st.text}
                      readOnly={approved}
                      rows={1}
                      onFocus={() => select({ section: si, statement: i })}
                      onBlur={() => select(null)}
                      onChange={(e) =>
                        update((d) => {
                          d.sections[si].statements[i].text = e.target.value;
                        })
                      }
                      className={`field-sizing-content w-full resize-none rounded-md px-2 py-1 text-sm leading-relaxed text-slate-800 outline-none transition-colors ${
                        isActive ? "bg-amber-50 ring-1 ring-amber-300" : "hover:bg-slate-50"
                      }`}
                    />
                    {!approved && (
                      <button
                        onClick={() =>
                          update((d) => {
                            d.sections[si].statements.splice(i, 1);
                          })
                        }
                        className="mt-1 px-1 text-slate-300 opacity-0 hover:text-red-600 group-hover:opacity-100"
                        aria-label="Remove line"
                      >
                        ×
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
            {!approved && (
              <button
                onClick={() =>
                  update((d) => {
                    d.sections[si].statements.push({ text: "", source_segment_ids: [] });
                  })
                }
                className="ml-3.5 mt-1 text-xs text-slate-400 hover:text-brand-700"
              >
                + Add line
              </button>
            )}
          </section>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-4">
        <p className="text-xs text-slate-500">
          {approved ? "Signed. Paste into the patient record." : "Click any line to see where it came from."}
        </p>
        <div className="flex items-center gap-2">
          {!approved && (
            <button
              onClick={onReview}
              disabled={reviewing}
              className="flex items-center gap-2 rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {reviewing && (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-700" />
              )}
              {reviewing ? "Checking…" : findings ? "Re-check" : "Safety check"}
            </button>
          )}
          <button
            onClick={approveAndCopy}
            className="rounded-full bg-brand-700 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-800"
          >
            {copied ? "Copied ✓" : approved ? "Copy again" : "Sign & copy"}
          </button>
        </div>
      </div>
    </div>
  );
}
