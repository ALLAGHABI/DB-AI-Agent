"""اتصالات محفوظة — كلمات المرور مشفرة ولا تُرجَع أبداً عبر HTTP."""
import json
import os
import uuid

from .errors import AppError, NotFoundError
from .secrets_store import SecretsStore

_SERVER_TYPES = {"mysql", "postgresql"}
_DRIVERS = {"mysql": "mysql+pymysql", "postgresql": "postgresql+psycopg"}
_DEFAULT_PORTS = {"mysql": "3306", "postgresql": "5432"}


class ConnectionsStore:
    """يخزن ملفات اتصال معنونة؛ كلمة المرور في SecretsStore مشفرة."""

    def __init__(self, data_dir: str = "data"):
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, "connections.json")
        self._secrets = SecretsStore(data_dir)
        self._items: list[dict] = []
        if os.path.exists(self._path):
            try:
                self._items = json.load(open(self._path, encoding="utf-8"))
            except Exception:
                self._items = []

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _public(item: dict) -> dict:
        """نسخة آمنة للعرض — بلا كلمة مرور."""
        return {k: v for k, v in item.items() if k != "has_password"} | {
            "has_password": bool(item.get("has_password"))}

    def list(self) -> list[dict]:
        return [self._public(i) for i in self._items]

    def add(self, *, name: str, type: str, sqlite_file: str = "", host: str = "",
            port: str = "", database: str = "", username: str = "",
            password: str = "") -> dict:
        name = name.strip()
        if not name:
            raise AppError("connectionNameRequired")
        if type == "sqlite":
            if not sqlite_file.strip():
                raise AppError("sqlitePathRequired")
        elif type in _SERVER_TYPES:
            if not (host.strip() and database.strip() and username.strip()):
                raise AppError("serverFieldsRequired")
        else:
            raise AppError("unknownDbType", type=type)

        item = {
            "id": uuid.uuid4().hex[:12], "name": name, "type": type,
            "sqlite_file": sqlite_file.strip(), "host": host.strip(), "port": port.strip(),
            "database": database.strip(), "username": username.strip(),
            "has_password": bool(password),
        }
        if password:
            self._secrets.set(f"conn_{item['id']}", password)
        self._items.append(item)
        self._save()
        return self._public(item)

    def get(self, conn_id: str) -> dict:
        for item in self._items:
            if item["id"] == conn_id:
                return item
        raise NotFoundError("connectionMissing")

    def delete(self, conn_id: str) -> None:
        item = self.get(conn_id)
        self._secrets.set(f"conn_{conn_id}", "")
        self._items.remove(item)
        self._save()

    def build_url(self, conn_id: str) -> str:
        item = self.get(conn_id)
        if item["type"] == "sqlite":
            return f"sqlite:///{item['sqlite_file']}"
        password = self._secrets.get(f"conn_{conn_id}")
        port = item["port"] or _DEFAULT_PORTS[item["type"]]
        driver = _DRIVERS[item["type"]]
        return (f"{driver}://{item['username']}:{password}"
                f"@{item['host']}:{port}/{item['database']}")
