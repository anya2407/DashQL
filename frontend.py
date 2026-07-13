import streamlit as st
import uuid
import html
import pandas as pd
import plotly.express as px

from main import chatbot

# -----------------------------
# Page Config
# -----------------------------

st.set_page_config(
    page_title="DashQL",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #FBFAF7;
        border: 1px solid #DAD6CB;
        border-radius: 12px;
        padding: 16px;
    }
    .dashql-insight {
        background-color: #EEEDFE;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 20px;
        color: #3C3489;
        font-size: 14px;
        line-height: 1.6;
    }
    .dashql-card {
        background-color: #FBFAF7;
        border: 1px solid #DAD6CB;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <h2 style="font-size: 28px; font-weight: 500; margin: 0; color: #2A2822;">📊 DashQL</h2>
    <p style="font-size: 14px; color: #7A7768; margin: 4px 0 0;">
        Ask for a dashboard, get it instantly — powered by natural language SQL generation
    </p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Session State
# -----------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

CONFIG = {
    "configurable": {
        "thread_id": st.session_state.thread_id
    }
}

if "history" not in st.session_state:
    st.session_state.history = []

DISPLAY_LIMIT = 20


# -----------------------------
# Shared rendering (used for both the live turn and history replay)
# -----------------------------

def render_result(result: dict):
    """Renders one assistant turn (insight/answer + dashboard) from a result dict."""

    layout = result.get("dashboard_layout") or []
    datasets = result.get("datasets") or {}

    if not layout and result.get("answer"):
        # Out-of-scope / DB-question case — just the message, no dashboard grid
        st.markdown(
            f'<div class="dashql-insight">💬 {html.escape(result["answer"])}</div>',
            unsafe_allow_html=True
        )
        return

    # ---- Insight banner ----
    if result.get("answer"):
        st.markdown(
            f'<div class="dashql-insight">💡 {html.escape(result["answer"])}</div>',
            unsafe_allow_html=True
        )

    # ---- KPI row ----
    kpis = [c for c in layout if c["type"] == "kpi"]
    others = [c for c in layout if c["type"] != "kpi"]

    if kpis:
        kpi_cols = st.columns(len(kpis))
        for i, component in enumerate(kpis):
            with kpi_cols[i]:
                df = pd.DataFrame(datasets.get(component["id"], []))
                value = df.iloc[0, 0] if not df.empty else "—"
                st.metric(component["title"], value)

    # ---- Charts + tables, 2-column grid ----
    for i in range(0, len(others), 2):
        row_components = others[i:i + 2]
        cols = st.columns(len(row_components))

        for col, component in zip(cols, row_components):
            with col:
                df = pd.DataFrame(datasets.get(component["id"], []))

                st.markdown(f'<div class="dashql-card">', unsafe_allow_html=True)
                st.markdown(f"**{component['title']}**")

                if df.empty:
                    st.caption("No data returned for this component.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    continue

                if component["type"] == "table":
                    if len(df) > DISPLAY_LIMIT:
                        st.caption(f"Showing first {DISPLAY_LIMIT} of {len(df)} rows")
                        st.dataframe(df.head(DISPLAY_LIMIT), use_container_width=True)
                    else:
                        st.dataframe(df, use_container_width=True)

                elif component["type"] == "chart":
                    chart = component.get("chart_type")
                    x = component.get("x")
                    y = component.get("y")

                    if not chart or x not in df.columns or y not in df.columns:
                        st.warning("This chart couldn't be rendered (missing or invalid fields).")
                        st.markdown("</div>", unsafe_allow_html=True)
                        continue

                    if chart == "line":
                        fig = px.line(df, x=x, y=y)
                    elif chart == "bar":
                        fig = px.bar(df, x=x, y=y)
                    elif chart == "pie":
                        fig = px.pie(df, names=x, values=y)
                    elif chart == "scatter":
                        fig = px.scatter(df, x=x, y=y)
                    else:
                        st.warning(f"Unsupported chart type: {chart}")
                        st.markdown("</div>", unsafe_allow_html=True)
                        continue

                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=260,
                        font=dict(color="#2A2822")
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{component['id']}")

                st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------
# Show Chat History
# -----------------------------

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_result(msg["result"])

# -----------------------------
# User Input
# -----------------------------

user_input = st.chat_input("Describe the dashboard you want...")

if user_input:

    st.session_state.history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):

        status = st.status("⚙️ Generating Dashboard...", expanded=True)

        initial_state = {
            "messages": [],
            "request": user_input,
            "dashboard_found": False,
            "dashboard_id": "",
            "dashboard_plan": [],
            "sql_queries": [],
            "datasets": {},
            "dashboard_layout": [],
            "progress": "",
            "answer": ""
        }

        result = None
        for step in chatbot.stream(initial_state, config=CONFIG, stream_mode="values"):
            if step.get("progress"):
                status.write(step["progress"])
            result = step

        status.update(label="✅ Dashboard Ready!", state="complete")

        if result.get("dashboard_layout"):
            st.success("Dashboard Generated!")

        render_result(result)

    # Persist the FULL result so this turn renders correctly on future reruns
    st.session_state.history.append({
        "role": "assistant",
        "result": {
            "answer": result.get("answer", ""),
            "dashboard_layout": result.get("dashboard_layout", []),
            "datasets": result.get("datasets", {}),
        }
    })