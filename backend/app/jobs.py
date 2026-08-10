"""مهام خلفية قصيرة العمر — لتوليد التقارير الذي قد يتجاوز مهلة أي وسيط HTTP."""
import threading
import uuid
from typing import Any, Callable

from .errors import AppError, NotFoundError

MAX_KEPT = 50


class JobStore:
    """سجل مهام في الذاكرة (تطبيق محلي أحادي العملية)."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def get(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError("jobMissing")
        return job

    def _set(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            self._jobs[job_id].update(fields)

    def run(self, work: Callable[[], dict]) -> str:
        """يشغّل العمل في خيط منفصل ويعيد معرّف المهمة فوراً."""
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._jobs[job_id] = {"id": job_id, "status": "running"}
            self._order.append(job_id)
            for old in self._order[:-MAX_KEPT]:
                self._jobs.pop(old, None)
            self._order = self._order[-MAX_KEPT:]

        def runner() -> None:
            try:
                self._set(job_id, status="done", result=work())
            except AppError as e:
                self._set(job_id, status="failed", error=e.to_detail())
            except Exception as e:                      # خطأ غير متوقع
                self._set(job_id, status="failed",
                          error={"code": "generic", "params": {"detail": str(e)}})

        threading.Thread(target=runner, daemon=True).start()
        return job_id
