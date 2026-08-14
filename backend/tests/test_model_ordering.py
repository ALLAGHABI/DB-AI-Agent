"""ترتيب نماذج Ollama: الأفضل لمهام الأداة أولاً، وبلا أسماء مكررة.

الواجهة تجعل أول القائمة هو الافتراضي — فالترتيب هنا قرار جودة مقيس،
لا ترتيباً أبجدياً ولا ترتيب التنزيل العشوائي.
"""
from app.llm.ollama import order_models


def _m(name, digest=None, size=0):
    return {"name": name, "digest": digest or name, "size": size}


def test_best_measured_model_comes_first():
    models = [_m("gemma3:1b"), _m("qwen3:8b"), _m("gemma3:4b"), _m("deepseek-r1:8b")]
    assert order_models(models)[0] == "gemma3:4b"


def test_tiny_model_goes_last_even_though_ollama_lists_it_first():
    """gemma3:1b يتجاهل اللغة ويختلق أرقاماً — لا يصلح افتراضياً أبداً."""
    models = [_m("gemma3:1b"), _m("gemma3:4b")]
    assert order_models(models) == ["gemma3:4b", "gemma3:1b"]


def test_alias_tags_collapse_to_the_explicit_name():
    """gemma3n:latest و gemma3n:e4b نفس البصمة — خيار واحد لا خياران."""
    models = [_m("gemma3n:latest", digest="abc"), _m("gemma3n:e4b", digest="abc"),
              _m("gemma3:4b")]
    out = order_models(models)
    assert "gemma3n:latest" not in out
    assert out.count("gemma3n:e4b") == 1


def test_unknown_models_follow_ranked_ones_by_size():
    models = [_m("mystery:7b", size=7), _m("gemma3:4b"), _m("mystery:70b", size=70)]
    assert order_models(models) == ["gemma3:4b", "mystery:70b", "mystery:7b"]
