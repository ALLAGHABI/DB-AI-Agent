import respx
from httpx import Response

from app.llm.ollama import OllamaProvider

BASE = "http://localhost:11434"


@respx.mock
async def test_status_lists_models():
    respx.get(f"{BASE}/api/tags").mock(return_value=Response(200, json={
        "models": [{"name": "gemma3:1b"}, {"name": "gpt-oss:20b"}]
    }))
    p = OllamaProvider(BASE)
    st = await p.status()
    assert st.available is True
    assert st.is_local is True
    assert "gpt-oss:20b" in st.models


@respx.mock
async def test_status_unreachable():
    respx.get(f"{BASE}/api/tags").mock(side_effect=Exception("refused"))
    st = await OllamaProvider(BASE).status()
    assert st.available is False
    assert st.models == []


@respx.mock
async def test_chat_returns_text():
    respx.post(f"{BASE}/api/chat").mock(return_value=Response(200, json={
        "message": {"role": "assistant", "content": "SELECT 1"}
    }))
    r = await OllamaProvider(BASE).chat("gemma3:1b", "sys", "user")
    assert r.text == "SELECT 1"
    assert r.provider == "ollama" and r.is_local is True
