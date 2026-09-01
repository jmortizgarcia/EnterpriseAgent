from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    provider: str = "ollama"
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    database_url: str = "sqlite:///data/sessions.db"
    vector_store: str = "chroma"
    database_url_pg: str = ""
    langsmith_api_key: str = ""
    environment: str = "development"
    google_cloud_project: str = ""
    google_cloud_region: str = "europe-west1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
