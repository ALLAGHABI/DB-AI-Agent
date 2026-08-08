from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str        # "ollama" | "openai_compat" | "openrouter"
    is_local: bool


@dataclass
class ProviderStatus:
    id: str
    label: str
    is_local: bool
    available: bool
    models: list[str] = field(default_factory=list)
    detail: str = ""     # human hint, e.g. "Ollama not reachable"


class LLMProvider(ABC):
    id: str
    label: str
    is_local: bool

    @abstractmethod
    async def status(self) -> ProviderStatus: ...

    @abstractmethod
    async def chat(self, model: str, system: str, user: str,
                   temperature: float = 0.1, max_tokens: int = 800) -> LLMResult: ...
