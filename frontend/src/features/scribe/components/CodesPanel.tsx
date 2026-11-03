"use client";

import { useState } from "react";
import { formatDateTime } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { EmptyState, Spinner } from "@/shared/ui/ui";
import { scribeApi } from "../api";
import type { ClinicalCode, SavedCodes } from "../types";

const KIND_LABEL: Record<ClinicalCode["kind"], string> = {
  primary: "Primary",
  secondary: "Secondary",
  symptom: "Symptom",
  history: "History / status",
};
const KIND_STYLE: Record<ClinicalCode["kind"], string> = {
  primary: "border-brand-200 bg-brand-700 text-white",
  secondary: "border-brand-200 bg-brand-50 text-brand-800",
  symptom: "border-amber-200 bg-amber-50 text-amber-800",
  history: "border-slate-200 bg-slate-50 text-slate-600",
};
const CONFIDENCE_STYLE: Record<ClinicalCode["confidence"], string> = {
  high: "text-emerald-700",
  medium: "text-amber-700",
  low: "text-rose-700",
};

export function CodesPanel({
  encounterId,
  initial,
  hasNote,
  signed,
  onChange,
}: {
  encounterId: string;
  initial: SavedCodes | null;
  hasNote: boolean;
  signed: boolean;
  /** Keeps the parent's copy current so the tab shows the latest list when reopened */
  onChange: (s: SavedCodes) => void;
}) {
  const [saved, setSaved] = useState<SavedCodes | null>(initial);
  function commit(next: SavedCodes) {
    setSaved(next);
    onChange(next);
  }
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      commit(await scribeApi.generateCodes(encounterId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not suggest codes");
    } finally {
      setBusy(false);
    }
  }

  async function remove(code: string) {
    if (!saved) return;
    const next = { ...saved, codes: saved.codes.filter((c) => c.code !== code) };
    commit(next);
    await scribeApi.saveCodes(encounterId, next).catch(() => setError("Could not save the change"));
  }

  if (!hasNote) {
    return (
      <EmptyState icon={<Icons.File />} title="No note yet">
        Codes are suggested from the clinical note. Generate the note first.
      </EmptyState>
    );
  }

  if (!saved) {
    return (
      <EmptyState icon={<Icons.Sparkles />} title="Suggest ICD-10-CM codes">
        <p>
          The model reads the {signed ? "signed" : "draft"} note and proposes diagnosis, symptom and history codes, each with the
          line that supports it.
        </p>
        {error && <p className="mt-2 text-rose-700">{error}</p>}
        <button
          onClick={generate}
          disabled={busy}
          className="mx-auto mt-4 flex items-center gap-2 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-60"
        >
          {busy ? (
            <Spinner className="h-4 w-4 border-white/30 border-t-white" />
          ) : (
            <Icons.Sparkles className="h-4 w-4 text-amber-300" />
          )}
          {busy ? "Suggesting codes…" : "Suggest codes"}
        </button>
      </EmptyState>
    );
  }

  const stale = signed && saved.source === "draft";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Clinical codes · ICD-10-CM</h3>
          <p className="text-xs text-slate-500">
            {saved.codes.length} suggested from the {saved.source} note · {formatDateTime(saved.generated_at)}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={async () => {
              await navigator.clipboard.writeText(saved.codes.map((c) => `${c.code} ${c.description}`).join("\n"));
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            disabled={!saved.codes.length}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Icons.Copy className="h-3.5 w-3.5" />
            {copied ? "Copied ✓" : "Copy codes"}
          </button>
          <button
            onClick={generate}
            disabled={busy}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {busy ? <Spinner className="h-3.5 w-3.5" /> : <Icons.Refresh className="h-3.5 w-3.5" />}
            Regenerate
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-2.5 text-xs text-amber-900">
        <Icons.Alert className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          AI-suggested codes. A clinician or coder must verify each one against the documentation before billing or submission.
          {stale && <strong> The note has been signed since these were generated — regenerate to code the final version.</strong>}
        </span>
      </div>

      {error && <p className="mb-3 text-sm text-rose-700">{error}</p>}

      {saved.codes.length === 0 ? (
        <EmptyState title="Nothing codeable was found in the note" />
      ) : (
        <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {saved.codes.map((c) => (
            <li key={c.code} className="group flex items-start gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3">
              <span className="w-20 shrink-0 pt-0.5 font-mono text-base font-bold text-slate-900">{c.code}</span>
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">{c.description}</span>
                  <span
                    className={`rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${KIND_STYLE[c.kind]}`}
                  >
                    {KIND_LABEL[c.kind]}
                  </span>
                </p>
                {c.evidence && <p className="mt-1 text-xs italic text-slate-500">&ldquo;{c.evidence}&rdquo;</p>}
              </div>
              <span className={`shrink-0 pt-0.5 text-xs font-semibold capitalize ${CONFIDENCE_STYLE[c.confidence]}`}>
                {c.confidence}
              </span>
              <button
                onClick={() => remove(c.code)}
                title="Remove this code"
                className="shrink-0 rounded-md p-1 text-slate-300 hover:bg-rose-50 hover:text-rose-600"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
