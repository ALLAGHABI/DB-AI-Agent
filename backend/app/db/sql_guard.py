from enum import Enum

import sqlglot
from sqlglot import exp
from ..errors import AppError


class SqlClass(str, Enum):
    READ = "read"
    WRITE = "write"
    DDL = "ddl"


_DDL = (exp.Create, exp.Drop, exp.Alter, exp.TruncateTable)
_WRITE = (exp.Insert, exp.Update, exp.Delete, exp.Merge)


def _parse_one(sql: str, dialect: str | None = None) -> exp.Expression:
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as e:
        raise AppError("sqlParseFailed", detail=str(e)) from e
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise AppError("singleStatementOnly")
    return statements[0]


def classify(sql: str, dialect: str | None = None) -> SqlClass:
    tree = _parse_one(sql, dialect)
    if isinstance(tree, _DDL):
        return SqlClass.DDL
    if isinstance(tree, _WRITE):
        return SqlClass.WRITE
    # CTE قد يغلف جملة كتابة — نفحص كامل الشجرة لا الجذر فقط
    for node in tree.walk():
        if isinstance(node, _DDL):
            return SqlClass.DDL
        if isinstance(node, _WRITE):
            return SqlClass.WRITE
    return SqlClass.READ


def ensure_limit(sql: str, max_rows: int, dialect: str | None = None) -> str:
    tree = _parse_one(sql, dialect)
    if classify(sql, dialect) != SqlClass.READ:
        return sql
    if isinstance(tree, exp.Select) and tree.args.get("limit") is None:
        return tree.limit(max_rows).sql(dialect=dialect)
    return sql
