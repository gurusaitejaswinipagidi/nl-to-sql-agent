"""
app.py
Streamlit UI for the NL-to-SQL Analytics Agent.
Features premium styling, interactive example question cards,
custom database uploading, step-by-step agent tracking, and self-healing logs.
"""
import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

# Allow running `streamlit run app.py` from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.sql_agent import run_agent, get_groq_client, get_schema

# Load environment variables (with override to support local .env)
load_dotenv(override=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sample.db")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "sample_query_results.csv")

st.set_page_config(page_title="NL-to-SQL Analytics Agent", page_icon="🗄️", layout="wide")

# Custom CSS for a beautiful, premium dark-mode aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Background Gradients */
    .stApp {
        background: linear-gradient(135deg, #0b0914 0%, #150e28 50%, #07050d 100%) !important;
        color: #f1ecfa !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(18, 12, 38, 0.8) !important;
        border-right: 1px solid rgba(124, 58, 237, 0.2) !important;
        backdrop-filter: blur(15px) !important;
    }
    
    /* Header Card styling */
    .header-card {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.15) 0%, rgba(79, 70, 229, 0.05) 100%);
        border: 1px solid rgba(124, 58, 237, 0.25);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    
    /* Custom Result Card */
    .result-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 24px;
        margin-top: 15px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Example Question Button Styling */
    div.stButton > button {
        background: linear-gradient(135deg, #2b1c4e 0%, #160d2b 100%) !important;
        color: #e2d9f3 !important;
        border: 1px solid rgba(124, 58, 237, 0.3) !important;
        border-radius: 10px !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        text-align: left !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 15px rgba(124, 58, 237, 0.4) !important;
        border-color: #a78bfa !important;
        color: #ffffff !important;
    }
    
    /* Text Area Styling */
    textarea {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(124, 58, 237, 0.2) !important;
        color: #f1ecfa !important;
        border-radius: 8px !important;
    }
    
    textarea:focus {
        border-color: #a78bfa !important;
        box-shadow: 0 0 8px rgba(167, 139, 250, 0.4) !important;
    }
    
    /* Gradient Text Header */
    .gradient-header {
        font-weight: 700;
        font-size: 2.8rem;
        background: linear-gradient(90deg, #c084fc, #6366f1, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize input field value in session state
if "question_input" not in st.session_state:
    st.session_state["question_input"] = ""

def set_question(q):
    st.session_state["question_input"] = q
    # Setting this directly syncs with the text area widget key
    st.session_state["main_question_input"] = q

# ---------------- Header Section ----------------
st.markdown("""
<div class="header-card">
    <div class="gradient-header">🗄️ NL-to-SQL Analytics Agent</div>
    <div style="font-size: 1.1rem; color: #b4a9d4; margin-top: 5px;">
        Empower business users with self-serve database insights. Type your question in plain English, 
        and the agent will read the schema, generate SQL, validate safety, execute, and plot the result.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar: Settings & Uploads ----------------
with st.sidebar:
    st.markdown("### ⚙️ Workspace Settings")

    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        value=os.environ.get("GROQ_API_KEY", ""),
        help="Get a free key from console.groq.com. Overrides existing environment values.",
    )
    if api_key_input:
        os.environ["GROQ_API_KEY"] = api_key_input

    st.divider()

    st.markdown("### 📁 Database Selection")
    db_source = st.radio(
        "Choose Database Source:",
        ("Default Sample DB", "Upload Custom SQLite DB"),
        index=0
    )

    active_db_path = DB_PATH

    if db_source == "Upload Custom SQLite DB":
        uploaded_file = st.file_uploader(
            "Upload SQLite database file (.db or .sqlite)",
            type=["db", "sqlite", "sqlite3"],
            help="Your database remains secure and is processed locally in read-only mode."
        )
        if uploaded_file is not None:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            uploaded_db_path = os.path.join(os.path.dirname(DB_PATH), "uploaded_temp.db")
            with open(uploaded_db_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            active_db_path = uploaded_db_path
            st.success("✅ Custom database loaded!")
        else:
            st.info("Please upload a file. Using default sample database until then.")
            active_db_path = DB_PATH
    else:
        active_db_path = DB_PATH

    st.divider()
    st.markdown("### 📋 Active Schema Details")
    
    if os.path.exists(active_db_path):
        try:
            schema_content = get_schema(active_db_path)
            with st.expander("Show Schema Details", expanded=False):
                st.text(schema_content)
        except Exception as e:
            st.error(f"Could not read database schema: {e}")
    else:
        st.error("Sample database not found. Run `python data/create_sample_db.py` first.")

# ---------------- Example Questions Grid ----------------
st.markdown("#### 💡 Quick Examples")
st.caption("Click any question below to automatically load and run it:")

examples = [
    {"label": "💰 Top 3 Customers", "question": "Which 3 customers have spent the most money in total?"},
    {"label": "📈 Category Revenue", "question": "Show total revenue by product category"},
    {"label": "📦 Best-Sellers", "question": "List the top 5 best-selling products by quantity"},
    {"label": "📅 June Orders", "question": "How many orders were placed in June 2024?"},
    {"label": "📊 Average Order Value", "question": "What is the average order value per customer?"}
]

# Display example question cards in columns
cols = st.columns(len(examples))
for i, ex in enumerate(examples):
    with cols[i]:
        if st.button(ex["label"], key=f"ex_btn_{i}"):
            set_question(ex["question"])
            st.rerun()

st.write("")  # Spacer

# ---------------- Main input area ----------------
question = st.text_area(
    "Your natural language question:",
    value=st.session_state["question_input"],
    placeholder="e.g. Which customers spent the most money in total?",
    height=90,
    key="main_question_input"
)

# Sync input area with session state on edit
if question != st.session_state["question_input"]:
    st.session_state["question_input"] = question

run_clicked = st.button("Run Analytics Agent", type="primary")

if run_clicked:
    if not os.environ.get("GROQ_API_KEY"):
        st.error("⚠️ Please enter a valid Groq API key in the sidebar.")
    elif not question.strip():
        st.warning("⚠️ Please type or select a question first.")
    elif not os.path.exists(active_db_path):
        st.error("⚠️ Database file not found.")
    else:
        # Agent execution status tracking container
        with st.status("Agent Executing...", expanded=True) as status:
            st.write("🔍 **Step 1:** Reading active database schema...")
            
            st.write("🧠 **Step 2:** Formulating SQLite query (using Llama 3.3)...")
            client = get_groq_client()
            
            # Execute run_agent which wraps schema tools, LLM calls, safety validation, and execution
            result = run_agent(question, active_db_path, client=client)
            
            st.write("🛡️ **Step 3:** Running SQL safety validation checks...")
            
            if len(result["attempts"]) > 1:
                st.write(f"⚠️ **Step 4:** Execution error detected. Initiating self-healing loop (attempt {len(result['attempts'])})...")
            else:
                st.write("📊 **Step 4:** Executing SQL against read-only SQLite database...")
                
            if result["success"]:
                status.update(label="✅ Run completed successfully!", state="complete", expanded=False)
            else:
                status.update(label="❌ Run failed after processing checks", state="error", expanded=False)

        # ---------------- Display Output Results ----------------
        if result["error"] and not result["success"]:
            st.error(f"**Error:** {result['error']}")
            if result["sql"]:
                st.subheader("Generated SQL (Failed)")
                st.code(result["sql"], language="sql")
                
            # If self-healing attempts were logged, show them
            if len(result["attempts"]) > 1:
                with st.expander("🛠️ Self-Healing Debug Logs", expanded=True):
                    for idx, att in enumerate(result["attempts"]):
                        status_symbol = "✅" if att["status"] == "success" else "❌"
                        st.markdown(f"**Attempt {att['attempt']}** {status_symbol}")
                        if att["sql"]:
                            st.code(att["sql"], language="sql")
                        if att["error"]:
                            st.error(f"Error details: {att['error']}")
                        st.divider()
        else:
            st.balloons()
            
            # Layout the results beautifully
            col_left, col_right = st.columns([1.2, 1.0])
            
            with col_left:
                st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                st.subheader("📋 Query Result Table")
                df = result["dataframe"]
                st.dataframe(df, use_container_width=True)
                
                # CSV Export Option
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                df.to_csv(OUTPUT_PATH, index=False)
                with open(OUTPUT_PATH, "rb") as f:
                    st.download_button(
                        "📥 Download Result as CSV",
                        data=f,
                        file_name="query_results.csv",
                        mime="text/csv",
                    )
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Show explanation
                if result["explanation"]:
                    st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                    st.subheader("💡 Agent Explanation")
                    st.markdown(result["explanation"])
                    st.markdown("</div>", unsafe_allow_html=True)

            with col_right:
                st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                st.subheader("⚙️ Generated SQL Query")
                st.code(result["sql"], language="sql")
                st.markdown("</div>", unsafe_allow_html=True)

                # Render Plotly Chart (if suggested and valid)
                chart_type = result.get("chart_suggestion", "none")
                x_col = result.get("x_axis")
                y_col = result.get("y_axis")

                if (
                    chart_type in ("bar", "line", "pie")
                    and x_col in df.columns
                    and y_col in df.columns
                    and len(df) > 0
                ):
                    st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                    st.subheader(f"📊 Suggested Chart: {chart_type.capitalize()}")
                    try:
                        # Keep charts styled sleekly
                        if chart_type == "bar":
                            fig = px.bar(df, x=x_col, y=y_col, template="plotly_dark", color_discrete_sequence=["#8b5cf6"])
                        elif chart_type == "line":
                            fig = px.line(df, x=x_col, y=y_col, template="plotly_dark", color_discrete_sequence=["#6366f1"])
                        elif chart_type == "pie":
                            fig = px.pie(df, names=x_col, values=y_col, template="plotly_dark", color_discrete_sequence=px.colors.sequential.Purples_r)
                        
                        fig.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=20, r=20, t=30, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.info(f"Could not render chart: {e}")
                    st.markdown("</div>", unsafe_allow_html=True)

            # If self-healing attempts were logged, show them below results
            if len(result["attempts"]) > 1:
                with st.expander("🛠️ Self-Healing Recovery Steps", expanded=False):
                    st.info("The agent encountered errors during SQL execution, but healed itself automatically using the compiler feedback.")
                    for idx, att in enumerate(result["attempts"]):
                        status_symbol = "✅" if att["status"] == "success" else "❌"
                        st.markdown(f"**Attempt {att['attempt']}** {status_symbol}")
                        if att["sql"]:
                            st.code(att["sql"], language="sql")
                        if att["error"]:
                            st.error(f"Execution Error: {att['error']}")
                        if att["explanation"] and att["status"] == "success":
                            st.success(f"Correction Explanation: {att['explanation']}")
                        st.divider()

st.divider()
st.markdown("<div style='text-align: center; color: #6b7280; font-size: 0.85rem;'>Developed for the AI Prototype Challenge — Data Engineering: NL-to-SQL Analytics Agent</div>", unsafe_allow_html=True)
