# NL-to-SQL Analytics Agent

**AI Prototype Challenge — Data Engineering Use Case**

> Business users keep pinging the data team for ad-hoc queries. This prototype lets users ask questions in plain English; an agent reads the database schema, generates SQL, validates it for safety, executes it against a read-only SQLite database, and returns the answer with the SQL used and a chart when appropriate.

---

## Features Implemented

- 🧠 **Schema-Grounded NL → SQL** using Groq's `llama-3.3-70b-versatile` model.
- 🛠️ **Self-Healing Agent Loop**: If a generated query fails validation or database execution (e.g., syntax or join issues), the agent intercepts the compiler feedback and automatically debugs and corrects itself (up to 2 retries).
- 📁 **Dynamic Database Uploader**: Allows users to upload their own SQLite databases (`.db` or `.sqlite` files) directly in the sidebar, view its schema details, and execute queries.
- 🔒 **SQL Safety Validation**: Ensures only `SELECT` or `WITH ... SELECT` queries are executed. Any dangerous keywords (like `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.) are blocked at the regex boundary.
- 🔐 **Read-Only Connection**: Second layer of database defense utilizing SQLite's native `mode=ro` connection settings.
- 📊 **Auto Plotly Chart Rendering**: Dynamically plots line, bar, or pie charts using custom dark themes when suggested by the LLM.
- 📥 **CSV Export**: Provides single-click CSV export and downloading for query results.
- 🎨 **Premium Aesthetic UI**: Re-styled Streamlit interface utilizing a custom dark violet/indigo gradient theme, modern Google Font `Outfit`, glowing hover transitions, interactive example cards, and dynamic step-by-step agent execution status tracking.

---

## Folder Structure

```
nl-to-sql-agent/
├── app.py                      # Premium Streamlit UI & flow controller
├── requirements.txt            # Python dependencies (groq, streamlit, pandas, etc.)
├── README.md                   # Setup, features, and walkthrough
├── prompts.md                  # System prompts and JSON response templates
├── ai_usage_note.md            # LLM assistance note (what helped, what went wrong)
├── team_info.md                # Submission details (academic info & team roles)
├── .env.example                # Template for environment credentials
│
├── data/
│   ├── create_sample_db.py     # Local database generator script
│   ├── sample.db               # Default SQLite database
│   └── sample_queries.json     # Documented input NL questions & expected SQL
│
├── resumes/
│   └── README.md               # Guide for submitting PDF resumes
│
├── outputs/
│   └── sample_query_results.csv # Exported query CSV
│
├── tests/
│   └── test_basic.py           # pytest suite (14 test cases including self-healing)
│
└── src/
    ├── __init__.py
    ├── schema_tool.py          # Formats database schema context for LLM grounding
    ├── sql_agent.py            # Core agent execution & self-healing retry loop
    └── safety_check.py         # Keyword & CTE safety boundary checking
```

---

## Setup Instructions

1. Clone the repository and enter the project folder:
   ```bash
   git clone <repo-url>
   cd nl-to-sql-agent
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Linux/Mac: source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your Groq API Key:
   - Copy `.env.example` to a new file named `.env`:
     ```bash
     copy .env.example .env
     ```
   - Edit `.env` and fill in your Groq API key:
     ```env
     GROQ_API_KEY=gsk_...
     ```
   - Alternatively, enter your key directly inside the Streamlit sidebar at runtime.

5. (Optional) Regenerate the sample database:
   ```bash
   python data/create_sample_db.py
   ```

---

## Run Instructions

Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

Open the local address in your web browser (usually `http://localhost:8501`).

---

## AI Capability Demonstrated

- **Agent Self-Healing (Reflection Loop)**: The agent loop does not fail silently. If a SQL statement causes a database compile error, the compiler feedback is fed directly back into the LLM context to recover, debug, and execute a corrected query. This is displayed transparently in the UI under **Self-Healing Recovery Steps**.
- **External Tool Grounding**: Uses the custom schema extraction tool to retrieve tables, types, and actual sample rows before reasoning.
- **Structured Outputs**: Leverages structured JSON response formatting (`sql`, `explanation`, `chart_suggestion`, `x_axis`, `y_axis`) to coordinate SQL execution and interactive Plotly rendering seamlessly.

---

## Running Tests

Execute the automated test suite covering safety checks, schema queries, read-only connections, and mocked self-healing behavior:
```bash
python -m pytest tests/test_basic.py -v
```

All 14 tests run and pass without requiring external API access (utilizing mocked completions where necessary).

---

## Submission Checklist (Infinite Round 3 Compliance)

- [ ] **Team Information**: Ensure [team_info.md](file:///C:/Users/ANIKET/Downloads/nl-to-sql-agent/nl-to-sql-agent/team_info.md) is filled out with member details and academic percentages.
- [ ] **Resumes Folder**: Ensure team PDF resumes are copied into the `resumes/` folder as detailed in [resumes/README.md](file:///C:/Users/ANIKET/Downloads/nl-to-sql-agent/nl-to-sql-agent/resumes/README.md).
- [ ] **Public GitHub Repo**: Verify this repository is set to public.
- [ ] **Demo Video**: Record a 5-7 minute demonstration showing:
  - Entering a question / clicking example cards.
  - Sidebar database uploading.
  - Agent step status tracking.
  - Plotly chart rendering & CSV downloading.
  - Self-healing recovery logs.
  - Insert link here: https://drive.google.com/file/d/1yJc8eeYQIsMIwCYxA61ztMLboUYKQdUM/view?usp=drivesdk
