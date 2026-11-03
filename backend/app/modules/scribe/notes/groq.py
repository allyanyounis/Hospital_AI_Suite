import asyncio
import json

import httpx
from pydantic import ValidationError

from .base import NoteGenerationError, T

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_ATTEMPTS = 3
MAX_WAIT_SECONDS = 30


class GroqNoteGenerator:
    """Groq-hosted open models (OpenAI-compatible API), e.g. openai/gpt-oss-120b."""

    name = "groq"

    def __init__(self, api_key: str, model: str, effort: str):
        self.api_key = api_key
        self.model = model
        self.effort = effort

    async def complete(self, system: str, user: str, schema: type[T], effort: str | None = None) -> T:
        json_schema = schema.model_json_schema()
        payload = {
            "model": self.model,
            "messages": [
                # The schema is repeated in the prompt so models without schema-constrained decoding still follow it
                {
                    "role": "system",
                    "content": f"{system}\n\nReply with JSON matching this schema:\n{json.dumps(json_schema)}",
                },
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": False},
            },
            "reasoning_effort": effort or self.effort,
            "temperature": 0,
            "max_completion_tokens": 16000,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                for attempt in range(MAX_ATTEMPTS):
                    resp = await client.post(
                        GROQ_URL, json=payload, headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                    if resp.status_code != 429 or attempt == MAX_ATTEMPTS - 1:
                        break
                    # Free-tier limits are per minute; wait as long as Groq asks (capped) and try again
                    await asyncio.sleep(min(float(resp.headers.get("retry-after", 10)), MAX_WAIT_SECONDS))
        except httpx.TimeoutException as e:
            raise NoteGenerationError("Groq took too long to respond") from e
        except httpx.HTTPError as e:
            raise NoteGenerationError("Could not reach the Groq API") from e

        if resp.status_code == 401:
            raise NoteGenerationError("Groq API key is invalid")
        if resp.status_code == 429:
            raise NoteGenerationError("Groq rate limit hit, try again shortly")
        if resp.status_code != 200:
            raise NoteGenerationError(f"Groq API error ({resp.status_code}): {resp.text[:300]}")

        try:
            choice = resp.json()["choices"][0]
            if choice.get("finish_reason") == "length":
                raise NoteGenerationError("The response was cut off; try a shorter recording")
            return schema.model_validate_json(choice["message"]["content"])
        except (KeyError, IndexError, TypeError, ValidationError) as e:
            raise NoteGenerationError("Groq returned an unreadable response; try again") from e
