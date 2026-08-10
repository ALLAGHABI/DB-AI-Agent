from .config import settings
from .connections_store import ConnectionsStore
from .db.manager import DatabaseManager
from .history import QueryHistory
from .jobs import JobStore
from .llm.ollama import OllamaProvider
from .llm.openai_compat import OpenAICompatProvider
from .llm.openrouter import OpenRouterProvider
from .secrets_store import SecretsStore


class AppState:
    def __init__(self):
        self.secrets = SecretsStore(settings.data_dir)
        self.db = DatabaseManager()
        self.history = QueryHistory(settings.data_dir)
        self.connections = ConnectionsStore(settings.data_dir)
        self.jobs = JobStore()

    def providers(self) -> list:
        return [
            OllamaProvider(settings.ollama_url),
            OpenAICompatProvider(self.secrets.get("openai_compat_url")),
            OpenRouterProvider(self.secrets.get("openrouter_api_key")),
        ]

    def provider_by_id(self, pid: str):
        for p in self.providers():
            if p.id == pid:
                return p
        raise KeyError(pid)


state = AppState()
