import json
import os

from cryptography.fernet import Fernet


class SecretsStore:
    """تخزين أسرار مشفر محلياً. القيم لا تُرجَع أبداً عبر HTTP — فقط has()."""

    def __init__(self, data_dir: str = "data"):
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, "secrets.json")
        key_path = os.path.join(data_dir, ".key")
        if os.path.exists(key_path):
            key = open(key_path, "rb").read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            os.chmod(key_path, 0o600)
        self._fernet = Fernet(key)
        self._data: dict[str, str] = {}
        if os.path.exists(self._path):
            try:
                self._data = json.load(open(self._path))
            except Exception:
                self._data = {}

    def set(self, name: str, value: str) -> None:
        if value:
            self._data[name] = self._fernet.encrypt(value.encode()).decode()
        else:
            self._data.pop(name, None)
        with open(self._path, "w") as f:
            json.dump(self._data, f)

    def get(self, name: str) -> str:
        enc = self._data.get(name, "")
        if not enc:
            return ""
        try:
            return self._fernet.decrypt(enc.encode()).decode()
        except Exception:
            return ""

    def has(self, name: str) -> bool:
        return bool(self.get(name))
