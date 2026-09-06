import asyncio

from app.config import Settings
from app.models import PlaceHint


class GeminiExtractor:
    def __init__(self, settings: Settings):
        self.project = settings.google_cloud_project
        self.location = settings.google_cloud_location
        self.model = settings.vertex_model

    @property
    def enabled(self) -> bool:
        return bool(self.project)

    async def extract_text(self, text: str) -> PlaceHint:
        if not self.enabled:
            return self._fallback(text)
        return await asyncio.to_thread(self._generate, [self._instruction(text)])

    async def extract_image(self, data: bytes, mime_type: str, source_url: str | None = None) -> PlaceHint:
        if not self.enabled:
            raise RuntimeError('vertex ai is not configured')

        from google.genai import types

        prompt = self._instruction(
            f'source url: {source_url}' if source_url else 'no source url provided'
        )
        parts = [
            prompt,
            types.Part.from_bytes(data=data, mime_type=mime_type),
        ]
        return await asyncio.to_thread(self._generate, parts)

    def _generate(self, contents) -> PlaceHint:
        from google import genai
        from google.genai import types

        client = genai.Client(
            enterprise=True,
            project=self.project,
            location=self.location,
            http_options=types.HttpOptions(api_version='v1'),
        )
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
        finally:
            client.close()

    @staticmethod
    def _instruction(source: str) -> str:
        return (
            'Extract the most likely real-world place from this saved artifact. '
            'Return only evidence visible or directly supported by the artifact. '
            'Do not guess an address, city, or category that is not supported. '
            'The name should be the place or business name, not the social account name, '
            'unless they are clearly the same place. '
            f'Artifact:\n{source}'
        )

    @staticmethod
    def _fallback(text: str) -> PlaceHint:
        clean = [line.strip(' -•\t') for line in text.splitlines() if line.strip()]
        if not clean:
            raise ValueError('could not extract a place hint')
        return PlaceHint(name=clean[0][:200], evidence=text[:1500])
