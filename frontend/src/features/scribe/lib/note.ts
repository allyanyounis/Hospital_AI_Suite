import type { Note } from "../types";

/** Plain-text note for the clipboard: HEADINGS with "- " lines. */
export function noteToText(note: Note): string {
  return note.sections
    .map((s) => {
      const lines = s.statements.map((st) => st.text.trim()).filter(Boolean);
      return `${s.heading.toUpperCase()}\n${lines.length ? lines.map((l) => `- ${l}`).join("\n") : "- Not discussed"}`;
    })
    .join("\n\n");
}
