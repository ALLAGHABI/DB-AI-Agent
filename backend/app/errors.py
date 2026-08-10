"""عقد أخطاء موحّد: الباكند يرسل رمزاً ومعاملات، والواجهة تترجمه للغة المستخدم.

لا نص عربي أو إنجليزي في الباكند — الترجمة مسؤولية الواجهة (messages/errors.*).
"""
from fastapi import HTTPException


class AppError(Exception):
    """خطأ يحمل رمزاً قابلاً للترجمة بدل رسالة بلغة واحدة."""

    status_code = 400

    def __init__(self, code: str, status_code: int | None = None, **params):
        self.code = code
        self.params = {k: str(v) for k, v in params.items()}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(code)

    def to_detail(self) -> dict:
        return {"code": self.code, "params": self.params}

    def to_http(self) -> HTTPException:
        return HTTPException(self.status_code, detail=self.to_detail())


class NotFoundError(AppError):
    status_code = 404


class ExecutionBlocked(AppError):
    """استعلام معدِّل بدون تأكيد صريح — يحمل الاستعلام وتصنيفه."""

    status_code = 409

    def __init__(self, sql_class: str, sql: str):
        self.sql_class = sql_class
        self.sql = sql
        super().__init__("writeNeedsConfirm")

    def to_detail(self) -> dict:
        return {"code": self.code, "params": {},
                "sql_class": self.sql_class, "sql": self.sql}


def http_error(code: str, status_code: int = 400, **params) -> HTTPException:
    return AppError(code, status_code, **params).to_http()
