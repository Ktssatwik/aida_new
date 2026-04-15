import json
from typing import Dict

def build_nl_to_sql_prompt(
        question : str , 
        table_name : str ,
        schema_json : str | None,
        value_hints: Dict[str, list[str]] | None = None ) -> str:
    
    try:
        schema_map: Dict[str, str] = json.loads(schema_json) if schema_json else {}
    except Exception:
        schema_map = {}

    schema_lines = "\n".join(
        [f"- {col} ({dtype})" for col, dtype in schema_map.items()]
    ) or "- (schema unavailable)"

    hints = value_hints or {}
    hint_lines = "\n".join(
        [f"- {col}: {', '.join(values)}" for col, values in hints.items()]
    ) or "- (no sampled values available)"

    return f"""
You are an expert MySQL SQL generator.

Rules you MUST follow:
1) Use ONLY this table: {table_name}
2) Use ONLY these columns:
{schema_lines}
3) Return exactly ONE SQL query.
4) Allowed query type: SELECT or WITH ... SELECT only.
5) Do NOT use: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE.
6) Do NOT use multiple statements.
7) If no limit is requested, include LIMIT 200.
8) Return ONLY raw SQL text (no markdown, no explanation).
9) Use exact column names only from the provided schema.
10) Prefer explicit column lists over SELECT * unless user asks for all columns.
11) When filtering categorical columns, prefer values from the sampled value list below.

Sample categorical values from this dataset:
{hint_lines}

User question:
{question}
""".strip()
