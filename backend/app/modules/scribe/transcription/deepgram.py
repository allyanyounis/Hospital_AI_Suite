import httpx

from .base import Segment, Transcript, TranscriptionError

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


class DeepgramTranscriber:
    name = "deepgram"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def transcribe(self, audio: bytes, mimetype: str) -> Transcript:
        params = {
            "model": self.model,
            "language": "en",
            "diarize": "true",
            "utterances": "true",
            "smart_format": "true",
            "punctuate": "true",
        }
        headers = {"Authorization": f"Token {self.api_key}", "Content-Type": mimetype}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(DEEPGRAM_URL, params=params, headers=headers, content=audio)
        if resp.status_code != 200:
            raise TranscriptionError(f"Deepgram returned {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        utterances = data.get("results", {}).get("utterances") or []
        segments = [
            Segment(
                id=i,
                speaker=u.get("speaker", 0),
                start=u["start"],
                end=u["end"],
                text=u["transcript"].strip(),
            )
            for i, u in enumerate(utterances)
            if u.get("transcript", "").strip()
        ]
        return Transcript(
            segments=segments,
            provider=self.name,
            duration=data.get("metadata", {}).get("duration"),
        )
