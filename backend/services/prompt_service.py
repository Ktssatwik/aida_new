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

    allowed_columns = list(schema_map.keys())
    allowed_columns_line = ", ".join([f"`{col}`" for col in allowed_columns]) or "(schema unavailable)"
    schema_lines = "\n".join(
        [f"- `{col}` ({dtype})" for col, dtype in schema_map.items()]
    ) or "- (schema unavailable)"
    schema_json_block = json.dumps(schema_map, indent=2) if schema_map else "{}"

    hints = value_hints or {}
    hint_lines = "\n".join(
        [f"- {col}: {', '.join(values)}" for col, values in hints.items()]
    ) or "- (no sampled values available)"

    return f"""
You are an expert MySQL SQL generator for a single uploaded dataset.

Your job is to convert the user's natural-language question into one valid MySQL read-only query.

Dataset context:
- Table name: `{table_name}`
- Allowed columns (exact names only): {allowed_columns_line}

Detailed schema:
{schema_lines}

Schema JSON:
{schema_json_block}

Rules you MUST follow:
1) Use ONLY this table: `{table_name}`.
2) Use ONLY column names that appear in the allowed column list and schema above.
3) Never invent, rename, pluralize, singularize, or guess a column name that is not explicitly listed.
4) If the user uses a business term or synonym, map it only to the closest listed column name.
5) Put backticks around the table name and every column name you use.
6) Return exactly ONE SQL query.
7) Allowed query type: SELECT or WITH ... SELECT only.
8) Do NOT use: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE.
9) Do NOT use multiple statements.
10) Return ONLY raw SQL text with no markdown, no explanation, and no comments.
11) Prefer explicit column lists over SELECT * unless the user clearly asks for all columns.
12) If the query returns regular rows and no limit is requested, include LIMIT 200.
13) When filtering categorical/text columns, prefer values from the sampled value list below.
14) Before writing the final SQL, verify that every referenced column in SELECT, WHERE, GROUP BY, ORDER BY, HAVING, and JOIN-free CTE logic exactly matches one of the allowed column names above.

Sample categorical values from this dataset:
{hint_lines}

User question:
{question}
""".strip()
