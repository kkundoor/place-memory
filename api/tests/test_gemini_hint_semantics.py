from app.clients.gemini import GeminiExtractor


def test_extraction_instruction_separates_place_type_from_activity():
    prompt = GeminiExtractor._instruction('saved screenshot')

    assert 'category_hint means the type of the named place itself' in prompt
    assert 'put that in activity_hint instead' in prompt
    assert 'set name to null' in prompt


def test_generate_retries_transient_api_failure(monkeypatch):
    from types import SimpleNamespace

    from google import genai
    from google.genai import errors

    from app.models import PlaceHint

    class FakeAPIError(Exception):
        def __init__(self, code):
            super().__init__(f'HTTP {code}')
            self.code = code

    attempts = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs)

            if len(attempts) < 3:
                raise FakeAPIError(503)

            return SimpleNamespace(
                parsed=PlaceHint(name='Example Place')
            )

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr(
        genai,
        'Client',
        lambda api_key: FakeClient(),
    )
    monkeypatch.setattr(errors, 'APIError', FakeAPIError)
    monkeypatch.setattr(
        'app.clients.gemini.time.sleep',
        lambda seconds: None,
    )

    extractor = GeminiExtractor(SimpleNamespace(
        gemini_api_key='test-key',
        gemini_model='test-model',
    ))

    result = extractor._generate(['artifact'])

    assert result.name == 'Example Place'
    assert len(attempts) == 3


def test_generate_does_not_retry_nontransient_api_failure(monkeypatch):
    from types import SimpleNamespace

    import pytest
    from google import genai
    from google.genai import errors

    class FakeAPIError(Exception):
        def __init__(self, code):
            super().__init__(f'HTTP {code}')
            self.code = code

    attempts = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs)
            raise FakeAPIError(400)

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr(
        genai,
        'Client',
        lambda api_key: FakeClient(),
    )
    monkeypatch.setattr(errors, 'APIError', FakeAPIError)
    monkeypatch.setattr(
        'app.clients.gemini.time.sleep',
        lambda seconds: None,
    )

    extractor = GeminiExtractor(SimpleNamespace(
        gemini_api_key='test-key',
        gemini_model='test-model',
    ))

    with pytest.raises(RuntimeError):
        extractor._generate(['artifact'])

    assert len(attempts) == 1
