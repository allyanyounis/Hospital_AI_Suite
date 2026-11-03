import anthropic

from .base import NoteGenerationError, T


class ClaudeNoteGenerator:
    name = "claude"

    def __init__(self, api_key: str, model: str, effort: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.effort = effort

    async def complete(self, system: str, user: str, schema: type[T], effort: str | None = None) -> T:
        try:
            response = await self.client.beta.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": effort or self.effort},
                output_format=schema,
                # On a safety-classifier decline, retry server-side on Anthropic's recommended fallback model
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise NoteGenerationError("Anthropic API key is invalid") from e
        except anthropic.RateLimitError as e:
            raise NoteGenerationError("Anthropic rate limit hit, try again shortly") from e
        except anthropic.APIStatusError as e:
            raise NoteGenerationError(f"Anthropic API error ({e.status_code}): {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise NoteGenerationError("Could not reach the Anthropic API") from e

        if response.stop_reason == "refusal":
            raise NoteGenerationError("The model declined this request")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise NoteGenerationError("The response was cut off; try a shorter recording")

        return response.parsed_output
