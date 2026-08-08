from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"          # local-only by default (security)
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    data_dir: str = "data"           # runtime data (encrypted secrets, history)
    ollama_url: str = "http://localhost:11434"
    row_limit: int = 500             # auto-LIMIT for unbounded SELECTs

    model_config = {"env_prefix": "SMARTDB_"}


settings = Settings()
