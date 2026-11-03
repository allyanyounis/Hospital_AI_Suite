import { useState } from "react";
import { Icons } from "@/shared/ui/icons";
import { EmptyState, Spinner } from "@/shared/ui/ui";
import type { EncounterDetail, Finding, Note, NoteTemplate } from "../types";
import { NotePanel } from "./NotePanel";
import { TranscriptPanel } from "./TranscriptPanel";

export function NoteTab({
  detail,
  note,
  templates,
  onStartDraft,
  onChange,
  onApprove,
  highlighted,
  onSelect,
  findings,
  reviewing,
  onReview,
  onDismissFindings,
}: {
  detail: EncounterDetail;
  note: Note | null;
  templates: NoteTemplate[];
  onStartDraft: (templateId: string) => void;
  onChange: (n: Note) => void;
  onApprove: () => Promise<boolean>;
  highlighted: Set<number>;
  onSelect: (ids: number[]) => void;
  findings: Finding[] | null;
  reviewing: boolean;
  onReview: () => void;
  onDismissFindings: () => void;
}) {
  const [templateId, setTemplateId] = useState(detail.template_id ?? "cardiology-clinic");

  if (detail.status === "drafting") {
    return (
      <EmptyState icon={<Spinner className="h-5 w-5" />} title="Drafting the note…">
        This usually takes under a minute. You can leave this page; the Board shows when it&apos;s ready.
      </EmptyState>
    );
  }

  if (!note || detail.status === "pending" || detail.status === "failed") {
    return (
      <EmptyState
        icon={detail.status === "failed" ? <Icons.Alert /> : <Icons.Sparkles />}
        title={detail.status === "failed" ? "The draft failed" : "No note yet"}
      >
        {detail.status === "failed" && detail.error && <p className="mb-3 text-rose-700">{detail.error}</p>}
        <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => onStartDraft(templateId)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
          >
            <Icons.Sparkles className="h-4 w-4 text-amber-300" />
            {detail.status === "failed" ? "Try again" : "Generate note"}
          </button>
        </div>
      </EmptyState>
    );
  }

  // Note beside the transcript so clicking a line shows where it came from
  return (
    <div className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[1.4fr_1fr]">
      <div className="flex min-h-[480px] flex-col">
        <NotePanel
          note={note}
          approved={detail.status === "signed"}
          onChange={onChange}
          onApprove={onApprove}
          onSelect={onSelect}
          findings={findings}
          reviewing={reviewing}
          onReview={onReview}
          onDismissFindings={onDismissFindings}
        />
      </div>
      <div className="hidden min-h-0 flex-col rounded-xl border border-slate-100 bg-slate-50/60 p-4 xl:flex">
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-500">Source transcript</p>
        <TranscriptPanel transcript={detail.transcript} clinicianSpeaker={detail.clinician_speaker} highlighted={highlighted} />
      </div>
    </div>
  );
}
