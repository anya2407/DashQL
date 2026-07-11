import streamlit as st
import uuid
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

st.title("📊 DashQL")

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

    st.session_state.history.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):

        status = st.status(
            "⚙️ Generating Dashboard...",
            expanded=True
        )

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
            result = step  # keeps updating; ends up holding the final state

        status.update(
            label="✅ Dashboard Ready!",
            state="complete"
        )

        layout = result["dashboard_layout"]
        datasets = result["datasets"]

        st.success("Dashboard Generated!")

        for component in layout:

            st.subheader(component["title"])

            df = datasets[component["id"]]

            if component["type"] == "table":

                st.dataframe(df)

            elif component["type"] == "kpi":

                st.metric(
                    component["title"],
                    df.iloc[0, 0]
                )

            elif component["type"] == "chart":

                chart = component["chart_type"]

                if chart == "line":

                    fig = px.line(
                        df,
                        x=component["x"],
                        y=component["y"]
                    )

                elif chart == "bar":

                    fig = px.bar(
                        df,
                        x=component["x"],
                        y=component["y"]
                    )

                elif chart == "pie":

                    fig = px.pie(
                        df,
                        names=component["x"],
                        values=component["y"]
                    )

                elif chart == "scatter":

                    fig = px.scatter(
                        df,
                        x=component["x"],
                        y=component["y"]
                    )

                else:

                    st.warning(
                        f"Unsupported chart type: {chart}"
                    )

                    continue

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

    st.session_state.history.append(
        {
            "role": "assistant",
            "content": "Dashboard generated successfully."
        }
    )