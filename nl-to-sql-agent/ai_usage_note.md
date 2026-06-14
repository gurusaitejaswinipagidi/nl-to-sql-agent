# AI Usage Note

## What AI helped with

- Generating the overall project scaffold (folder structure, requirements.txt).
- Writing the SQLite schema reader (`schema_tool.py`) that formats table/column
  info + sample rows for LLM grounding.
- Writing the SQL safety validator (`safety_check.py`) that blocks any
  non-SELECT statement before execution.
- Designing the system prompt that forces the LLM to return structured JSON
  (sql, explanation, chart_suggestion, x_axis, y_axis).
- Writing the agent loop (`sql_agent.py`) that ties schema reading → LLM call
  → validation → execution together.
- Building the Streamlit UI (`app.py`) including sidebar schema viewer,
  chart rendering, and CSV export.
- Writing pytest test cases covering schema reading, safety checks, and
  end-to-end agent execution.
- Generating realistic sample data for the customers/products/orders tables.

## What AI got wrong / had to be corrected

- Initial draft of the safety check used simple substring matching for
  forbidden keywords (e.g. "DROP"), which would false-positive on column
  names like `dropdown_id`. This was corrected using word-boundary regex
  (`\bDROP\b`).
- The first version of the JSON-parsing logic assumed the LLM would never
  wrap its response in markdown code fences. In practice some models do this
  occasionally, so `_extract_json()` now strips ```json fences and uses a
  regex to locate the JSON object before parsing.
- Needed to explicitly specify `mode=ro` (read-only) on the SQLite connection
  used for execution — relying only on the LLM/agent-level safety check is
  not sufficient defense-in-depth.

## Best prompts used

- The structured-JSON system prompt (see `prompts.md`) was key — asking the
  LLM to return `sql`, `explanation`, `chart_suggestion`, `x_axis`, `y_axis`
  in one JSON object made it trivial to drive both the SQL execution and the
  Plotly chart rendering from a single LLM call.
- Including 1-2 sample rows per table (not just column names/types) in the
  schema text noticeably improved SQL correctness, especially for filtering
  on text values (e.g. city names, category names) since the model could see
  the actual casing/format used in the data.
