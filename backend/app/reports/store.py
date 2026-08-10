"""أرشيف التقارير وملفات التحليل المؤقتة."""
import json
import os
import pickle
import shutil
import time
import uuid

import pandas as pd
from ..errors import AppError, NotFoundError


class ReportStore:
    def __init__(self, data_dir: str = "data"):
        self.root = os.path.join(data_dir, "reports")
        self.tmp = os.path.join(self.root, ".tmp")
        os.makedirs(self.tmp, exist_ok=True)

    # ---------- ملفات التحليل المؤقتة (بين خطوتي analyze/generate) ----------

    def save_temp(self, df: pd.DataFrame, source_name: str) -> str:
        token = uuid.uuid4().hex
        with open(os.path.join(self.tmp, f"{token}.pkl"), "wb") as f:
            pickle.dump({"df": df, "source_name": source_name, "ts": time.time()}, f)
        self._cleanup_temp()
        return token

    def load_temp(self, token: str) -> tuple[pd.DataFrame, str]:
        path = os.path.join(self.tmp, f"{os.path.basename(token)}.pkl")
        if not os.path.exists(path):
            raise NotFoundError("analysisExpired")
        with open(path, "rb") as f:
            data = pickle.load(f)
        return data["df"], data["source_name"]

    def _cleanup_temp(self, ttl: float = 3600):
        now = time.time()
        for name in os.listdir(self.tmp):
            path = os.path.join(self.tmp, name)
            if now - os.path.getmtime(path) > ttl:
                os.remove(path)

    # ---------- الأرشيف ----------

    def create(self, meta: dict, html: str, xlsx: bytes,
               pdf: bytes | None) -> str:
        report_id = uuid.uuid4().hex[:12]
        d = os.path.join(self.root, report_id)
        os.makedirs(d)
        meta = {**meta, "id": report_id, "pdf": pdf is not None}
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        with open(os.path.join(d, "report.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(d, "report.xlsx"), "wb") as f:
            f.write(xlsx)
        if pdf:
            with open(os.path.join(d, "report.pdf"), "wb") as f:
                f.write(pdf)
        return report_id

    def list(self) -> list[dict]:
        out = []
        for name in os.listdir(self.root):
            meta_path = os.path.join(self.root, name, "meta.json")
            if os.path.exists(meta_path):
                try:
                    out.append(json.load(open(meta_path, encoding="utf-8")))
                except Exception:
                    continue
        return sorted(out, key=lambda m: m.get("created_at", ""), reverse=True)

    def get_file(self, report_id: str, kind: str) -> bytes:
        names = {"html": "report.html", "xlsx": "report.xlsx", "pdf": "report.pdf"}
        if kind not in names:
            raise AppError("unknownFileKind", kind=kind)
        path = os.path.join(self.root, os.path.basename(report_id), names[kind])
        if not os.path.exists(path):
            raise NotFoundError("fileMissing")
        with open(path, "rb") as f:
            return f.read()

    def delete(self, report_id: str) -> None:
        d = os.path.join(self.root, os.path.basename(report_id))
        if not os.path.isdir(d):
            raise NotFoundError("reportMissing")
        shutil.rmtree(d)
