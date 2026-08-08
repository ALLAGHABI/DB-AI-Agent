from .base import ProviderStatus
from .openai_compat import OpenAICompatProvider


class OpenRouterProvider(OpenAICompatProvider):
    """الخيار السحابي الثاني — يتطلب مفتاح API."""
    id = "openrouter"
    label = "OpenRouter (سحابي)"
    is_local = False

    CURATED_MODELS = [
        "anthropic/claude-sonnet-4.5",
        "anthropic/claude-3.5-haiku",
        "openai/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "meta-llama/llama-3.3-70b-instruct",
    ]

    def __init__(self, api_key: str):
        super().__init__("https://openrouter.ai/api/v1", api_key)

    async def status(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(self.id, self.label, False, False, [],
                                  detail="أدخل مفتاح OpenRouter لتفعيل الخيار السحابي")
        return ProviderStatus(self.id, self.label, False, True, self.CURATED_MODELS)
