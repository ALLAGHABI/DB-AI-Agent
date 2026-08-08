from app.secrets_store import SecretsStore


def test_roundtrip_and_masking(tmp_path):
    s = SecretsStore(data_dir=str(tmp_path))
    s.set("openrouter_api_key", "sk-or-SECRET")
    assert s.get("openrouter_api_key") == "sk-or-SECRET"
    # الملف على القرص لا يحتوي السر نصاً صريحاً
    raw = (tmp_path / "secrets.json").read_text()
    assert "sk-or-SECRET" not in raw
    # has() لا يكشف القيمة
    assert s.has("openrouter_api_key") is True
    assert s.has("missing") is False


def test_empty_value_clears(tmp_path):
    s = SecretsStore(data_dir=str(tmp_path))
    s.set("k", "v")
    s.set("k", "")
    assert s.has("k") is False
