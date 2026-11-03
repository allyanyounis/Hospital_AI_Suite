/** Plain-language explanations of the planner's suggestions (ported from the POC's wording). */

import type { Move, Suggestion } from "../types";
import { dayLabel, hm, span } from "./time";

const longDay = (day: string) => dayLabel(day, { weekday: "long", day: "numeric", month: "long" });

/** Where a displaced case should go and why that day was chosen. `roomCode` names the destination theatre. */
export function placeLine(s: Move | Suggestion, roomCode: string): string {
  const hours = s.hours ? `rostered ${hm(s.hours[0])}–${hm(s.hours[1])}` : "rostered that day";
  const who = s.same_surgeon
    ? `${s.surgeon}, ${hours}`
    : `${s.surgeon}, ${hours}. The listed surgeon does not operate that day`;
  const extra = s.dest.expected_over ? `, about ${s.dest.expected_over} min overtime` : "";
  let text =
    `Put ${s.name} in ${roomCode} on ${longDay(s.date)}, booked ${hm(s.slot_start)}–${hm(s.slot_end)}, with ${who}. ` +
    `The planned length is ${span(s.minutes)}, from ${s.source}. Each later list was played 2,000 times with that ` +
    `length added. This day stays at ${s.dest.over_pct}% past 16:00${extra}.`;
  if (s.alt) {
    const altExtra = s.alt.expected_over ? `, about ${s.alt.expected_over} min overtime` : "";
    text += ` ${longDay(s.alt.day)} is sooner (booked ${hm(s.alt.start)}), but that list would be ${s.alt.over_pct}% past 16:00${altExtra}, so it was not used.`;
  } else if (s.dest.over_pct <= s.threshold) {
    text += " This is the soonest day the case fits a rostered surgeon.";
  } else {
    text += " No other staffed day in the next two weeks is safer.";
  }
  if (s.later)
    text += ` ${longDay(s.later.day)} would be ${s.later.over_pct}% past 16:00. This day is already under ${s.threshold}%, so the case is not held until then.`;
  return text;
}
