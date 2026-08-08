import re

SYSTEM_TEMPLATE = """You are an expert SQL generator for a {dialect} database.
Convert the user's natural-language request (Arabic or English) into exactly ONE SQL statement.

Rules:
- Return ONLY the SQL statement, inside a ```sql fenced block.
- Use only tables/columns that exist in the schema below.
- Never invent columns. If the request is ambiguous, prefer a simple SELECT.
- Do not add explanations.

Database schema:
{schema}"""


def build_prompt(schema: str, dialect: str) -> str:
    return SYSTEM_TEMPLATE.format(schema=schema, dialect=dialect)


def extract_sql(raw: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
    sql = m.group(1) if m else raw
    lines = [l for l in sql.splitlines()
             if l.strip() and not l.strip().startswith("--")]
    return "\n".join(lines).strip().rstrip(";")
