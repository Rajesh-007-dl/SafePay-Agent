import streamlit as st
import json
import os
import pandas as pd

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="SafePay AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. CUSTOM CSS (The "Pro" Look) ---
st.markdown(
    """
<style>
    /* Global Styles */
    .stApp {
        background-color: #0e1117;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    
    /* Metrics Cards */
    .metric-container {
        background-color: #1e2127;
        border: 1px solid #2b303b;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-container:hover {
        transform: translateY(-2px);
        border-color: #4facfe;
    }
    .metric-label {
        color: #9ca3af;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 5px;
    }

    /* Status Badges */
    .badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-green { background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }
    .badge-orange { background-color: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid #f97316; }
    .badge-red { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }

    /* Timeline Styles */
    .timeline-item {
        border-left: 2px solid #374151;
        padding-left: 20px;
        padding-bottom: 25px;
        position: relative;
    }
    .timeline-item:last-child { border-left: none; }
    .timeline-dot {
        position: absolute;
        left: -6px;
        top: 0;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #6b7280;
    }
    .timeline-dot.success { background-color: #4ade80; box-shadow: 0 0 8px #4ade80; }
    .timeline-dot.failed { background-color: #f87171; box-shadow: 0 0 8px #f87171; }
    .timeline-dot.looping { background-color: #60a5fa; box-shadow: 0 0 8px #60a5fa; }
    
    .agent-name {
        font-weight: 600;
        color: #e5e7eb;
        font-size: 1rem;
    }
    .agent-detail {
        color: #9ca3af;
        font-size: 0.9rem;
        margin-top: 4px;
        background: #1f2937;
        padding: 8px;
        border-radius: 6px;
        border-left: 3px solid #374151;
    }
    .agent-detail.looping {
        border-left-color: #60a5fa;
        background: rgba(96, 165, 250, 0.1);
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- 3. DATA LOADING ---
@st.cache_data
def load_data():
    if os.path.exists("output/results.json"):
        with open("output/results.json", "r") as f:
            return json.load(f)
    return []


data = load_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SafePay")
    st.markdown("---")

    if not data:
        st.error("❌ No data found. Run pipeline first.")
        st.stop()

    # Create a nice list of invoices
    invoice_map = {item["source_file"]: item for item in data}
    selected_file = st.radio(
        "Select Invoice", list(invoice_map.keys()), format_func=lambda x: f"📄 {x}"
    )

    st.markdown("---")

    # System Health
    st.markdown("### System Health")
    st.success("Orchestrator: **Online**")
    st.info(f"Database: **{len(data)} Records**")
    st.caption("SafePay Engine v1.0 ")

# --- 5. MAIN CONTENT ---
record = invoice_map[selected_file]
res = record["processing_results"]
action = res["recommended_action"]
trace = res.get("agent_execution_trace", [])

# Determine Status Badge
if action == "auto_approve":
    badge_class = "badge-green"
    badge_text = "✅ AUTO APPROVED"
elif action == "flag_for_review":
    badge_class = "badge-orange"
    badge_text = "⚠️ FLAGGED FOR REVIEW"
else:
    badge_class = "badge-red"
    badge_text = "🛑 ESCALATED"

# Header Row
c1, c2 = st.columns([3, 1])
with c1:
    st.title(f"Invoice Analysis: {record.get('invoice_id', 'N/A')}")
    st.caption(f"Source File: {selected_file}")
with c2:
    st.markdown(
        f'<div style="text-align:right; margin-top:10px;"><span class="badge {badge_class}">{badge_text}</span></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# Metrics Grid
m1, m2, m3, m4 = st.columns(4)

with m1:
    conf = res["extraction_confidence"]
    color = "#4ade80" if conf > 0.9 else "#fb923c"
    st.markdown(
        f"""
        <div class="metric-container">
            <div class="metric-label">AI Confidence</div>
            <div class="metric-value" style="color: {color}">{conf:.1%}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with m2:
    po = res["matching_results"]["matched_po"] or "N/A"
    st.markdown(
        f"""
        <div class="metric-container">
            <div class="metric-label">Matched PO</div>
            <div class="metric-value">{po}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with m3:
    disc = len(res.get("discrepancies", []))
    d_color = "#f87171" if disc > 0 else "#4ade80"
    st.markdown(
        f"""
        <div class="metric-container">
            <div class="metric-label">Discrepancies</div>
            <div class="metric-value" style="color: {d_color}">{disc}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with m4:
    items = len(res["extracted_data"]["line_items"])
    st.markdown(
        f"""
        <div class="metric-container">
            <div class="metric-label">Line Items</div>
            <div class="metric-value">{items}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

st.write("")  # Spacer

# Content Split
left_col, right_col = st.columns([1.5, 1])

# --- LEFT COLUMN: DATA & INSIGHTS ---
with left_col:
    st.subheader("📋 Line Item Extraction")
    if res["extracted_data"]["line_items"]:
        df = pd.DataFrame(res["extracted_data"]["line_items"])
        st.dataframe(
            df,
            column_config={
                "unit_price": st.column_config.NumberColumn(
                    "Unit Price", format="$%.2f"
                ),
                "line_total": st.column_config.NumberColumn("Total", format="$%.2f"),
                "confidence": st.column_config.ProgressColumn(
                    "Confidence", format="%.2f", min_value=0, max_value=1
                ),
            },
            hide_index=True,
            use_container_width=True,
        )

    st.write("")

    # Dynamic Section: Show Discrepancies OR Hybrid Search
    if res.get("discrepancies"):
        st.subheader("🚨 Risk Detected")
        for d in res["discrepancies"]:
            st.error(f"**{d['type'].replace('_',' ').title()}**: {d['details']}")

    # Show Candidates (Crucial for Invoice 5)
    candidates = res["matching_results"].get("candidates_considered", [])
    if candidates and len(candidates) > 1:
        st.subheader("🔍 Hybrid Search Candidates")
        st.info("The agent considered multiple POs due to fuzzy matching logic:")
        c_df = pd.DataFrame(candidates)
        st.dataframe(
            c_df,
            column_config={
                "confidence": st.column_config.ProgressColumn(
                    "Score", format="%.2f", min_value=0, max_value=1
                )
            },
            hide_index=True,
        )

# --- RIGHT COLUMN: AGENT TRACE (TIMELINE) ---
with right_col:
    st.subheader("🧠 Neural Activity")

    with st.container(height=600, border=True):
        for step in trace:
            status = step["status"]
            # Map status to style
            if status in ["Success", "Passed", "Clean", "Complete"]:
                dot_class = "success"
                icon = ""
            elif status in ["Failed", "No Match", "Flagged"]:
                dot_class = "failed"
                icon = "⚠️ "
            elif status == "Looping":
                dot_class = "looping"
                icon = "🔄 "
            else:
                dot_class = ""
                icon = ""

            # Special highlighting for the Loop
            detail_class = "looping" if status == "Looping" else ""

            st.markdown(
                f"""
            <div class="timeline-item">
                <div class="timeline-dot {dot_class}"></div>
                <div class="agent-name">{step['agent']} <span style="font-size:0.8em; opacity:0.7; float:right;">{status}</span></div>
                <div class="agent-detail {detail_class}">
                    {icon}{step['detail']}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
