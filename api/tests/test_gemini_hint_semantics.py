from app.clients.gemini import GeminiExtractor


def test_extraction_instruction_separates_place_type_from_activity():
    prompt = GeminiExtractor._instruction('saved screenshot')

    assert 'category_hint means the type of the named place itself' in prompt
    assert 'put that in activity_hint instead' in prompt
    assert 'set name to null' in prompt
