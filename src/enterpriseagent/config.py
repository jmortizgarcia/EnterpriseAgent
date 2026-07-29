from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    provider: str = "claude"
    database_url: str = "sqlite:///data/sessions.db"
    langsmith_api_key: str = ""
    environment: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
