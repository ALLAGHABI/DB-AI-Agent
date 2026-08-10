"""سجل الاستعلامات — يُحفظ محلياً في SQLite بجانب بيانات التطبيق."""
import datetime
import os
import sqlite3
from dataclasses import asdict, dataclass

from .errors import NotFoundError

MAX_ENTRIES = 500


@dataclass
class HistoryEntry:
    id: int
    request: str | None      # طلب اللغة الطبيعية إن وُجد
    sql: str
    sql_class: str
    source: str              # "nl" | "editor"
    model: str | None
    rows: int
    success: bool
    created_at: str
    favorite: bool


class QueryHistory:
    def __init__(self, data_dir: str = "data"):
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "history.db")
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request TEXT,
                    sql TEXT NOT NULL,
                    sql_class TEXT NOT NULL,
                    source TEXT NOT NULL,
                    model TEXT,
                    rows INTEGER NOT NULL DEFAULT 0,
                    success INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    favorite INTEGER NOT NULL DEFAULT 0
                )
            """)

    def add(self, *, sql: str, sql_class: str, source: str, request: str | None = None,
            model: str | None = None, rows: int = 0, success: bool = True) -> int:
        created = datetime.datetime.now().astimezone().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO query_history"
                " (request, sql, sql_class, source, model, rows, success, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (request, sql, sql_class, source, model, rows, int(success), created))
            # تقليم السجل مع الاحتفاظ بالمفضلات دائماً
            conn.execute(
                "DELETE FROM query_history WHERE favorite = 0 AND id NOT IN"
                " (SELECT id FROM query_history WHERE favorite = 0"
                "  ORDER BY id DESC LIMIT ?)", (MAX_ENTRIES,))
            return int(cur.lastrowid)

    def list(self, limit: int = 50, favorites_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM query_history"
        if favorites_only:
            sql += " WHERE favorite = 1"
        sql += " ORDER BY id DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [
            asdict(HistoryEntry(
                id=r["id"], request=r["request"], sql=r["sql"], sql_class=r["sql_class"],
                source=r["source"], model=r["model"], rows=r["rows"],
                success=bool(r["success"]), created_at=r["created_at"],
                favorite=bool(r["favorite"])))
            for r in rows
        ]

    def set_favorite(self, entry_id: int, favorite: bool) -> None:
        with self._connect() as conn:
            cur = conn.execute("UPDATE query_history SET favorite = ? WHERE id = ?",
                               (int(favorite), entry_id))
            if cur.rowcount == 0:
                raise NotFoundError("historyEntryMissing")

    def delete(self, entry_id: int) -> None:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM query_history WHERE id = ?", (entry_id,))
            if cur.rowcount == 0:
                raise NotFoundError("historyEntryMissing")

    def clear(self, keep_favorites: bool = True) -> int:
        sql = "DELETE FROM query_history"
        if keep_favorites:
            sql += " WHERE favorite = 0"
        with self._connect() as conn:
            return int(conn.execute(sql).rowcount)
