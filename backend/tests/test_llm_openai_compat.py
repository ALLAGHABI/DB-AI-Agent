import respx
from httpx import Response

from app.llm.openai_compat import OpenAICompatProvider
from app.llm.openrouter import OpenRouterProvider

BASE = "http://localhost:1234/v1"


@respx.mock
async def test_compat_status_and_chat():
    respx.get(f"{BASE}/models").mock(return_value=Response(200, json={
        "data": [{"id": "qwen2.5-coder"}]
    }))
    respx.post(f"{BASE}/chat/completions").mock(return_value=Response(200, json={
        "choices": [{"message": {"content": "SELECT 2"}}]
    }))
    p = OpenAICompatProvider(BASE)
    st = await p.status()
    assert st.available and st.is_local and st.models == ["qwen2.5-coder"]
    r = await p.chat("qwen2.5-coder", "sys", "user")
    assert r.text == "SELECT 2" and r.is_local is True


@respx.mock
async def test_openrouter_is_cloud_and_needs_key():
    p = OpenRouterProvider(api_key="")
    st = await p.status()
    assert st.available is False and st.is_local is False

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "SELECT 3"}}]}))
    p2 = OpenRouterProvider(api_key="sk-or-test")
    r = await p2.chat("anthropic/claude-3.5-haiku", "sys", "user")
    assert r.text == "SELECT 3" and r.is_local is False
