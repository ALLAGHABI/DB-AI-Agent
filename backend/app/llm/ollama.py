import httpx

from .base import LLMProvider, LLMResult, ProviderStatus

# ترتيب أفضلية مقيس فعلياً على مهمتَي الأداة (تقرير عربي ملتزم بالأرقام + NL→SQL):
# gemma3:4b كتب التقرير في 60ث بلا اختلاق، وe2b في 87ث؛ نماذج التفكير المطوّل
# (qwen3، deepseek) تصلح لكنها أبطأ بكثير؛ وgemma3:1b يختلق أرقاماً فيأتي أخيراً.
# الواجهة تجعل أول القائمة هو الافتراضي، فالترتيب قرار جودة لا تجميل.
_PREFERENCE = ("gemma3:4b", "gemma3n:e2b", "gemma3n:e4b", "qwen2.5",
               "qwen3", "deepseek-r1", "gemma3:1b")


def _rank(name: str, size: int) -> tuple:
    low = name.lower()
    for i, hint in enumerate(_PREFERENCE):
        if low.startswith(hint):
            return (0, i, -size)
    return (1, 0, -size)


def order_models(models: list[dict]) -> list[str]:
    """يرتب للأفضلية ويطوي الأسماء المكررة لنموذج واحد.

    `gemma3n:latest` و`gemma3n:e4b` نفس البصمة — عرضهما معاً يوحي بخيارين
    مختلفين، ونُبقي الاسم الصريح لأنه يخبر المستخدم بحجم ما يشغّله.
    """
    by_digest: dict[str, dict] = {}
    for m in models:
        key = m.get("digest") or m["name"]
        kept = by_digest.get(key)
        if not kept or (kept["name"].endswith(":latest")
                        and not m["name"].endswith(":latest")):
            by_digest[key] = m
    unique = sorted(by_digest.values(),
                    key=lambda m: _rank(m["name"], m.get("size", 0)))
    return [m["name"] for m in unique]


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
                models = order_models(r.json().get("models", []))
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
        # النماذج فوق 5GB قد تحتاج أكثر من دقيقتين لكتابة تقرير على جهاز عادي —
        # مهلة ضيقة تحوّل نموذجاً بطيئاً إلى «معطوب» زوراً. التوليد مهمة خلفية
        # ذات استطلاع، فالمهلة الأسخى لا تحجب الواجهة.
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            text = r.json()["message"]["content"]
        return LLMResult(text=text, model=model, provider=self.id, is_local=True)
