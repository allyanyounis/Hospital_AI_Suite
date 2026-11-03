"use client";

import { useState } from "react";
import { scribeApi } from "../api";
import type { DocumentType, GeneratedDocument } from "../types";

export function DocumentsPanel({
  encounterId,
  types,
  onError,
}: {
  encounterId: string;
  types: DocumentType[];
  onError: (message: string) => void;
}) {
  const [docs, setDocs] = useState<Record<string, GeneratedDocument>>({});
  const [activeType, setActiveType] = useState<string | null>(null);
  const [busyType, setBusyType] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function generate(typeId: string) {
    setActiveType(typeId);
    if (docs[typeId]) return;
    setBusyType(typeId);
    try {
      const doc = await scribeApi.document(encounterId, typeId);
      setDocs((d) => ({ ...d, [typeId]: doc }));
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not write the document");
    } finally {
      setBusyType(null);
    }
  }

  function updateParagraph(i: number, text: string) {
    if (!activeType) return;
    setDocs((d) => {
      const doc = d[activeType];
      return { ...d, [activeType]: { ...doc, paragraphs: doc.paragraphs.map((p, j) => (j === i ? text : p)) } };
    });
  }

  async function copy() {
    if (!active) return;
    await navigator.clipboard.writeText([active.title, ...active.paragraphs].join("\n\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  const active = activeType ? docs[activeType] : undefined;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 flex flex-wrap gap-2">
        {types.map((t) => (
          <button
            key={t.id}
            onClick={() => generate(t.id)}
            disabled={busyType !== null}
            title={t.description}
            className={`rounded-full border px-4 py-1.5 text-sm ${
              activeType === t.id
                ? "border-brand-700 bg-brand-50 text-brand-800"
                : "border-slate-300 text-slate-700 hover:bg-slate-50"
            } disabled:opacity-50`}
          >
            {t.name}
          </button>
        ))}
      </div>

      {busyType ? (
        <p className="flex flex-1 items-center justify-center gap-3 text-sm text-slate-500">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-700" />
          Writing from the approved note…
        </p>
      ) : active ? (
        <>
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
            <h3 className="text-sm font-semibold text-slate-900">{active.title}</h3>
            {active.paragraphs.map((p, i) => (
              <textarea
                key={i}
                value={p}
                onChange={(e) => updateParagraph(i, e.target.value)}
                className="field-sizing-content w-full resize-none rounded-md px-2 py-1 text-sm leading-relaxed text-slate-800 outline-none hover:bg-slate-50 focus:bg-slate-50"
              />
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-4">
            <p className="text-xs text-slate-500">Fill in any [bracketed] details and check before sending.</p>
            <button
              onClick={copy}
              className="rounded-full bg-brand-700 px-5 py-2 text-sm font-medium text-white hover:bg-brand-800"
            >
              {copied ? "Copied ✓" : "Copy"}
            </button>
          </div>
        </>
      ) : (
        <p className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
          Choose a document. It is written only from the note you approved.
        </p>
      )}
    </div>
  );
}
