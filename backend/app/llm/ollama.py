import httpx

from .base import LLMProvider, LLMResult, ProviderStatus


class OllamaProvider(LLMProvider):
    id = "ollama"
    label = "Ollama (محلي)"
    is_local = True

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def status(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                models = [m["name"] for m in r.json().get("models", [])]
                return ProviderStatus(self.id, self.label, True, True, models)
        except Exception as e:
            return ProviderStatus(self.id, self.label, True, False, [],
                                  detail=f"Ollama غير متاح على {self.base_url}: {e}")

    async def chat(self, model: str, system: str, user: str,
                   temperature: float = 0.1, max_tokens: int = 800) -> LLMResult:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            text = r.json()["message"]["content"]
        return LLMResult(text=text, model=model, provider=self.id, is_local=True)
