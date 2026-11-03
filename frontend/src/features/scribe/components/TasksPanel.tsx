"use client";

import { useRef, useState } from "react";
import { formatDateTime } from "@/shared/lib/format";
import { Icons } from "@/shared/ui/icons";
import { EmptyState, Spinner } from "@/shared/ui/ui";
import { scribeApi } from "../api";
import type { CareTask, SavedTasks, TaskCategory } from "../types";

const CATEGORIES: { key: TaskCategory; label: string; tone: string }[] = [
  { key: "test", label: "Tests & investigations", tone: "bg-sky-50 text-sky-700" },
  { key: "medication", label: "Medications", tone: "bg-violet-50 text-violet-700" },
  { key: "referral", label: "Referrals", tone: "bg-brand-50 text-brand-700" },
  { key: "follow_up", label: "Follow-up", tone: "bg-amber-50 text-amber-700" },
  { key: "patient_advice", label: "Patient actions", tone: "bg-emerald-50 text-emerald-700" },
  { key: "admin", label: "Admin", tone: "bg-slate-100 text-slate-600" },
];

export function TasksPanel({
  encounterId,
  initial,
  hasNote,
  signed,
  onChange,
}: {
  encounterId: string;
  initial: SavedTasks | null;
  hasNote: boolean;
  signed: boolean;
  /** Keeps the parent's copy current so the tab shows the latest list when reopened */
  onChange: (s: SavedTasks) => void;
}) {
  const [saved, setSaved] = useState<SavedTasks | null>(initial);
  function commit(next: SavedTasks) {
    setSaved(next);
    onChange(next);
  }
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newCategory, setNewCategory] = useState<TaskCategory>("follow_up");
  const saveChain = useRef<Promise<unknown>>(Promise.resolve());

  async function generate() {
    if (
      saved?.tasks.some((t) => t.done) &&
      !confirm("Regenerating replaces the list, including ticked and added tasks. Continue?")
    )
      return;
    setBusy(true);
    setError(null);
    try {
      commit(await scribeApi.generateTasks(encounterId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not build the task list");
    } finally {
      setBusy(false);
    }
  }

  function update(tasks: CareTask[]) {
    if (!saved) return;
    const next = { ...saved, tasks };
    commit(next);
    // Serialise saves so a quick series of ticks lands in order
    saveChain.current = saveChain.current
      .then(() => scribeApi.saveTasks(encounterId, next))
      .catch(() => setError("Could not save the change"));
  }

  if (!hasNote) {
    return (
      <EmptyState icon={<Icons.File />} title="No note yet">
        The task list is built from the plan in the clinical note. Generate the note first.
      </EmptyState>
    );
  }

  if (!saved) {
    return (
      <EmptyState icon={<Icons.CheckCircle />} title="Build the follow-up task list">
        <p>
          Tests to order, medicine changes, referrals, follow-up and patient actions, pulled from the{" "}
          {signed ? "signed" : "draft"} note.
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
          {busy ? "Building tasks…" : "Build task list"}
        </button>
      </EmptyState>
    );
  }

  const tasks = saved.tasks;
  const done = tasks.filter((t) => t.done).length;
  const pct = tasks.length ? Math.round((100 * done) / tasks.length) : 0;
  const stale = signed && saved.source === "draft";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Task list</h3>
          <p className="text-xs text-slate-500">
            From the {saved.source} note · {formatDateTime(saved.generated_at)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-40">
            <div className="mb-1 flex justify-between text-xs">
              <span className="font-semibold text-slate-700">
                {done} of {tasks.length} done
              </span>
              <span className="tabular-nums text-slate-400">{pct}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${pct}%` }} />
            </div>
          </div>
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

      {stale && (
        <p className="mb-3 rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-2 text-xs text-amber-900">
          The note has been signed since this list was built. Regenerate if the plan changed.
        </p>
      )}
      {error && <p className="mb-3 text-sm text-rose-700">{error}</p>}

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {tasks.length === 0 && <EmptyState title="The note has no follow-up actions" />}
        {CATEGORIES.map((cat) => {
          const items = tasks.map((t, i) => ({ t, i })).filter(({ t }) => t.category === cat.key);
          if (!items.length) return null;
          return (
            <section key={cat.key}>
              <h4 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                <span className={`rounded-md px-1.5 py-0.5 ${cat.tone}`}>{cat.label}</span>
                <span className="font-normal normal-case tracking-normal text-slate-400">
                  {items.filter(({ t }) => t.done).length}/{items.length}
                </span>
              </h4>
              <ul className="space-y-1.5">
                {items.map(({ t, i }) => (
                  <li
                    key={i}
                    className={`group flex items-start gap-3 rounded-xl border px-4 py-3 transition-colors ${t.done ? "border-slate-100 bg-slate-50" : "border-slate-200 bg-white"}`}
                  >
                    <button
                      onClick={() => update(tasks.map((x, j) => (j === i ? { ...x, done: !x.done } : x)))}
                      aria-label={t.done ? "Mark as not done" : "Mark as done"}
                      className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-colors ${
                        t.done ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300 hover:border-brand-500"
                      }`}
                    >
                      {t.done && <Icons.Check className="h-3 w-3" />}
                    </button>
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-semibold ${t.done ? "text-slate-400 line-through" : "text-slate-900"}`}>
                        {t.title}
                      </p>
                      {t.detail && <p className={`text-xs ${t.done ? "text-slate-400" : "text-slate-600"}`}>{t.detail}</p>}
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1 text-[11px]">
                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 font-semibold capitalize text-slate-600">
                        {t.owner}
                      </span>
                      {t.due && (
                        <span className="flex items-center gap-1 text-slate-500">
                          <Icons.Clock className="h-3 w-3" />
                          {t.due}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => update(tasks.filter((_, j) => j !== i))}
                      title="Remove task"
                      className="shrink-0 rounded-md p-1 text-slate-300 hover:bg-rose-50 hover:text-rose-600"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!newTitle.trim()) return;
          update([
            ...tasks,
            { title: newTitle.trim(), detail: "", category: newCategory, owner: "clinician", due: "", done: false },
          ]);
          setNewTitle("");
        }}
        className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4"
      >
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Add a task…"
          maxLength={200}
          className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-600"
        />
        <select
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value as TaskCategory)}
          className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
        >
          {CATEGORIES.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>
        <button
          disabled={!newTitle.trim()}
          className="flex items-center gap-1 rounded-lg bg-brand-700 px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
        >
          <Icons.Plus className="h-3.5 w-3.5" />
          Add
        </button>
      </form>
    </div>
  );
}
