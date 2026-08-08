import httpx

from .base import LLMProvider, LLMResult, ProviderStatus


class OpenAICompatProvider(LLMProvider):
    """أي خادم محلي متوافق مع OpenAI API — LM Studio, vLLM, llama.cpp server."""
    id = "openai_compat"
    label = "خادم محلي متوافق OpenAI"
    is_local = True

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def status(self) -> ProviderStatus:
        if not self.base_url:
            return ProviderStatus(self.id, self.label, self.is_local, False, [],
                                  detail="لم يُحدد عنوان الخادم")
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self.base_url}/models", headers=self._headers())
                r.raise_for_status()
                models = [m["id"] for m in r.json().get("data", [])]
                return ProviderStatus(self.id, self.label, self.is_local, True, models)
        except Exception as e:
            return ProviderStatus(self.id, self.label, self.is_local, False, [], detail=str(e))

    async def chat(self, model: str, system: str, user: str,
                   temperature: float = 0.1, max_tokens: int = 800) -> LLMResult:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}/chat/completions",
                                  json=payload, headers=self._headers())
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        return LLMResult(text=text, model=model, provider=self.id, is_local=self.is_local)
