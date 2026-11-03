import httpx
from pydantic import ValidationError

from .base import NoteGenerationError, T


class OllamaNoteGenerator:
    """Runs an open model on this machine via Ollama. Nothing leaves the laptop."""

    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system: str, user: str, schema: type[T], effort: str | None = None) -> T:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            # Constrains decoding to the schema, so the reply is always parseable JSON
            "format": schema.model_json_schema(),
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 16384},
        }
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as e:
            raise NoteGenerationError("Ollama isn't running. Start the Ollama app and try again") from e
        except httpx.TimeoutException as e:
            raise NoteGenerationError("The local model took too long to respond") from e
        if resp.status_code == 404:
            raise NoteGenerationError(f"Model '{self.model}' isn't downloaded. Run: ollama pull {self.model}")
        if resp.status_code != 200:
            raise NoteGenerationError(f"Ollama returned {resp.status_code}: {resp.text[:300]}")

        try:
            return schema.model_validate_json(resp.json()["message"]["content"])
        except (KeyError, ValidationError) as e:
            raise NoteGenerationError("The local model returned an unreadable response; try again") from e

    async def is_ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
            return any(m["name"] == self.model for m in resp.json().get("models", []))
        except (httpx.HTTPError, ValueError):
            return False
