"""Live (streaming) transcription through Deepgram's WebSocket API.

The browser streams compressed audio chunks (webm/opus or mp4) to our backend, which relays them to Deepgram and
relays results back. Audio is never stored: chunks pass straight through memory to the provider.
"""

import json
from urllib.parse import urlencode

from websockets.asyncio.client import ClientConnection, connect

from .base import Segment

DEEPGRAM_LIVE_URL = "wss://api.deepgram.com/v1/listen"


def open_deepgram_stream(api_key: str, model: str):
    """Async context manager yielding a Deepgram streaming connection."""
    params = {
        "model": model,
        "language": "en",
        "diarize": "true",
        "punctuate": "true",
        "smart_format": "true",
        "interim_results": "true",
        # Sends an UtteranceEnd event after 1s of silence so we can close a speaker's turn
        "utterance_end_ms": "1000",
        "vad_events": "true",
    }
    return connect(
        f"{DEEPGRAM_LIVE_URL}?{urlencode(params)}",
        additional_headers={"Authorization": f"Token {api_key}"},
        max_size=None,
        open_timeout=10,
    )


async def send_control(dg: ClientConnection, kind: str) -> None:
    """Deepgram control messages: KeepAlive (while paused) and CloseStream (flush and finish)."""
    await dg.send(json.dumps({"type": kind}))


class LiveTranscriptBuilder:
    """Turns Deepgram's finalized streaming results into the same Segment list the batch transcriber returns.

    Consecutive words from one speaker are joined into one segment until the speaker changes or their turn ends
    (speech_final / UtteranceEnd), so the live transcript reads like the batch one.
    """

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self._turn_open = False

    def add_final(self, words: list[dict], speech_final: bool) -> list[Segment]:
        """Add the words of one is_final result; return the segments that were created or extended."""
        changed: dict[int, Segment] = {}
        for w in words:
            text = (w.get("punctuated_word") or w.get("word") or "").strip()
            if not text:
                continue
            speaker = int(w.get("speaker", 0))
            last = self.segments[-1] if self.segments else None
            if last is not None and self._turn_open and last.speaker == speaker:
                last.text = f"{last.text} {text}"
                last.end = float(w["end"])
            else:
                last = Segment(
                    id=len(self.segments), speaker=speaker, start=float(w["start"]), end=float(w["end"]), text=text
                )
                self.segments.append(last)
            self._turn_open = True
            changed[last.id] = last
        if speech_final:
            self.close_turn()
        return list(changed.values())

    def close_turn(self) -> None:
        self._turn_open = False

    @property
    def duration(self) -> float | None:
        return self.segments[-1].end if self.segments else None
