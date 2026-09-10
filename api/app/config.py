from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = 'local'
    database_path: str = 'place_memory.db'
    google_maps_api_key: str = ''
    google_cloud_project: str = ''
    google_cloud_location: str = 'us-central1'
    vertex_model: str = 'gemini-2.5-flash'
    web_origin: str = 'http://localhost:5173'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()
