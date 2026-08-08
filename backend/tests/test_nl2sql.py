from app.agent.nl2sql import build_prompt, extract_sql


def test_build_prompt_contains_schema_and_dialect():
    system = build_prompt(schema="TABLE t (a INT)", dialect="sqlite")
    assert "TABLE t (a INT)" in system
    assert "sqlite" in system.lower()


def test_extract_sql_from_fenced_block():
    raw = "Here you go:\n```sql\nSELECT *\nFROM t\n```\nEnjoy!"
    assert extract_sql(raw) == "SELECT *\nFROM t"


def test_extract_sql_plain_text():
    assert extract_sql("  SELECT 1;  ") == "SELECT 1"


def test_extract_sql_strips_line_comments():
    raw = "```sql\n-- count rows\nSELECT count(*) FROM t\n```"
    assert extract_sql(raw) == "SELECT count(*) FROM t"
