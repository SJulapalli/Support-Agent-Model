from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    voyage_api_key: str
    database_url: str
    shop_admin_url: str = "http://localhost:5173/admin"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore[call-arg]
