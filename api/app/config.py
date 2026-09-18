from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = 'local'
    database_path: str = 'place_memory.db'
    upload_dir: str = 'uploads'
    google_maps_api_key: str = ''
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-3.6-flash'
    photon_base_url: str = 'https://photon.komoot.io'
    photon_user_agent: str = 'place-memory/0.2 (+https://github.com/kkundoor/place-memory)'
    nominatim_base_url: str = 'https://nominatim.openstreetmap.org'
    nominatim_user_agent: str = 'place-memory/0.1 (+https://github.com/kkundoor/place-memory)'
    web_origin: str = 'http://localhost:5173'
    static_dir: str = ''

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()
