import asyncio
import logging
import time

from app.config import Settings
from app.models import PlaceHint


logger = logging.getLogger('place_memory.gemini')
_RETRY_DELAYS_SECONDS = (0.5, 1.0)


class GeminiExtractor:
    def __init__(self, settings: Settings):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def extract_text(self, text: str) -> PlaceHint:
        if not self.enabled:
            return self._fallback(text)
        return await asyncio.to_thread(self._generate, [self._instruction(text)])

    async def extract_image(
        self,
        data: bytes,
        mime_type: str,
        source_url: str | None = None,
        context: str | None = None,
    ) -> PlaceHint:
        if not self.enabled:
            raise RuntimeError('gemini api is not configured')

        from google.genai import types

        source_parts = [
            f'source url: {source_url}' if source_url else 'no source url provided',
        ]
        if context:
            source_parts.append(
                'User-provided context (this may not be visible in the image): '
                f'{context}'
            )

        prompt = self._instruction('\n'.join(source_parts))
        prompt += (
            '\nFor image inputs, keep visual evidence separate from user-provided context. '
            'Context may support extraction, but do not claim it was visible in the image.'
        )
        parts = [
            prompt,
            types.Part.from_bytes(data=data, mime_type=mime_type),
        ]
        return await asyncio.to_thread(self._generate, parts)

    def _generate(self, contents) -> PlaceHint:
        from google import genai
        from google.genai import errors
        from google.genai import types

        for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
            client = genai.Client(api_key=self.api_key)
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type='application/json',
                        response_schema=PlaceHint,
                    ),
                )
                parsed = response.parsed
                return parsed if isinstance(parsed, PlaceHint) else PlaceHint.model_validate(parsed)
            except errors.APIError as exc:
                code = getattr(exc, 'code', None)
                retryable = (
                    code in {408, 425, 429}
                    or (isinstance(code, int) and code >= 500)
                )

                if not retryable or attempt >= len(_RETRY_DELAYS_SECONDS):
                    raise RuntimeError('gemini request failed; retry shortly') from exc

                delay = _RETRY_DELAYS_SECONDS[attempt]
                logger.warning(
                    'gemini_request_retry code=%s attempt=%s delay=%s',
                    code,
                    attempt + 1,
                    delay,
                )
                time.sleep(delay)
            finally:
                client.close()

    @staticmethod
    def _instruction(source: str) -> str:
        return (
            'Extract the most likely specific real-world place from this saved artifact. '
            'Return only evidence visible or directly supported by the artifact. '
            'Do not guess an address, city, category, activity, or identity that is not supported. '
            'The name must be a specific place or business name, not a generic category. '
            'If no specific place or business identity is visible or directly supported, set name to null. '
            'category_hint means the type of the named place itself, for example lake, museum, cafe, '
            'restaurant, bakery, park, or stadium. Do not put an activity in category_hint. '
            'If an activity is explicitly shown or stated, such as boat rental, hiking, coffee, or kayaking, '
            'put that in activity_hint instead. Generic phrases such as coffee shop or bakery may be used as '
            'category_hint only when no more specific entity type is supported. '
            'Do not treat a social account name or search suggestion as the place unless the artifact clearly '
            'supports that they refer to the depicted/saved place. '
            f'Artifact:\n{source}'
        )

    @staticmethod
    def _fallback(text: str) -> PlaceHint:
        clean = [line.strip(' -•\t') for line in text.splitlines() if line.strip()]
        if not clean:
            raise ValueError('could not extract a place hint')
        return PlaceHint(name=clean[0][:200], evidence=text[:1500])
