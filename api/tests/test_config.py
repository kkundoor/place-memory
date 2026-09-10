from app.config import Settings


def test_web_origin_defaults_to_local_frontend():
    settings = Settings(_env_file=None)

    assert settings.web_origin == 'http://localhost:5173'


def test_web_origin_can_be_configured_for_deployment():
    settings = Settings(_env_file=None, web_origin='https://places.example.com')

    assert settings.web_origin == 'https://places.example.com'
