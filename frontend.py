import streamlit as st
import uuid
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

# -----------------------------
# Show Chat History
# -----------------------------

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

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

        for step in chatbot.stream(initial_state, config=CONFIG, stream_mode="values"):
            if step.get("progress"):
                status.write(step["progress"])
            result = step

        status.update(label="✅ Dashboard Ready!", state="complete")

        layout = result["dashboard_layout"]
        datasets = result["datasets"]

        if not layout and result.get("answer"):
            # Out-of-scope case — just show the message, skip dashboard rendering
            st.markdown(
                f'<div class="dashql-insight">💬 {result["answer"]}</div>',
                unsafe_allow_html=True
            )
            st.stop()

        st.success("Dashboard Generated!")

        # ---- Insight banner ----
        if result.get("answer"):
            st.markdown(
                f'<div class="dashql-insight">💡 {result["answer"]}</div>',
                unsafe_allow_html=True
            )

        # ---- KPI row ----
        kpis = [c for c in layout if c["type"] == "kpi"]
        others = [c for c in layout if c["type"] != "kpi"]

        if kpis:
            kpi_cols = st.columns(len(kpis))
            for i, component in enumerate(kpis):
                with kpi_cols[i]:
                    df = pd.DataFrame(datasets[component["id"]])
                    st.metric(component["title"], df.iloc[0, 0])

        # ---- Charts + tables, 2-column grid ----
        DISPLAY_LIMIT = 20

        for i in range(0, len(others), 2):
            row_components = others[i:i + 2]
            cols = st.columns(len(row_components))

            for col, component in zip(cols, row_components):
                with col:
                    df = pd.DataFrame(datasets[component["id"]])

                    st.markdown(f'<div class="dashql-card">', unsafe_allow_html=True)
                    st.markdown(f"**{component['title']}**")

                    if component["type"] == "table":
                        if len(df) > DISPLAY_LIMIT:
                            st.caption(f"Showing first {DISPLAY_LIMIT} of {len(df)} rows")
                            st.dataframe(df.head(DISPLAY_LIMIT), use_container_width=True)
                        else:
                            st.dataframe(df, use_container_width=True)

                    elif component["type"] == "chart":
                        chart = component["chart_type"]

                        if chart == "line":
                            fig = px.line(df, x=component["x"], y=component["y"])
                        elif chart == "bar":
                            fig = px.bar(df, x=component["x"], y=component["y"])
                        elif chart == "pie":
                            fig = px.pie(df, names=component["x"], values=component["y"])
                        elif chart == "scatter":
                            fig = px.scatter(df, x=component["x"], y=component["y"])
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
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.history.append({
        "role": "assistant",
        "content": "Dashboard generated successfully."
    })