import streamlit as st
import pandas as pd
import altair as alt
from dotenv import load_dotenv
import os
from openai import OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Workout Trends", "Upload CSV"])

# --- Main App Title ---
st.title("🏋️ Workout Dashboard")
st.subheader("Track your training progress with data insights")

# --- Pages ---
if page == "Home":
    st.markdown("""
    Welcome to your personal workout tracker.

    - 📊 Analyze progress
    - 📈 Visualize volume & intensity
    - 🗂 Upload CSVs from Strong or other apps
    """)

elif page == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your Strong .csv export", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Data preview:", df.head())

elif page == "Workout Trends":
    # --- Load and prep data ---
    try:
        df = pd.read_csv("env/analysis_output.csv")
    except FileNotFoundError:
        st.warning("No workout data found. Upload a CSV first.")
        st.stop()

    df["week_start"] = pd.to_datetime(df["week_start"])
    df["month_start"] = pd.to_datetime(df["month_start"])

    if "total_reps" in df.columns:
        df["total_reps"] = pd.to_numeric(df["total_reps"], errors="coerce").fillna(0).astype(int)
    else:
        st.error("❌ 'total_reps' column not found in uploaded file.")
        st.stop()

    # --- Dropdown: Date Granularity ---
    st.markdown("### 🗓️ Select Time Granularity")
    date_grouping = st.radio("Group data by", ["Weekly", "Monthly"])
    date_col = "week_start" if date_grouping == "Weekly" else "month_start"

    # --- Dropdown 1: Metric ---
    st.markdown("### 📐 Select a Metric to Display")
    metric_options = {
        "Total Volume": "total_volume",
        "Average RPE": "sum_rpe",   # divide by set count
        "Total Reps": "total_reps"
    }
    selected_metric_label = st.selectbox("Choose a metric", list(metric_options.keys()))
    selected_metric = metric_options[selected_metric_label]

    # --- Dropdown 2: Group By ---
    st.markdown("### 📊 Group By")
    group_options = {
        "Exercise Name": "exercise_name",
        "Body Part": "body_part"
    }

    # --- Filter to exercises with 5+ records ---
    exercise_counts = df["exercise_name"].value_counts()
    valid_exercises = exercise_counts[exercise_counts >= 25].index.tolist()
    df = df[df["exercise_name"].isin(valid_exercises)]
    

    selected_group_label = st.selectbox("Group data by", list(group_options.keys()))
    selected_group = group_options[selected_group_label]


    # --- Dropdown 3: Filter ---
    st.markdown("### 🎯 Filter Results")
    filter_list = sorted(df[selected_group].dropna().unique())
    selected_filter = st.selectbox("Choose one", filter_list)
    df = df[df[selected_group] == selected_filter]

    # --- Prepare for chart ---
    df["exercise"] = 1  # for averaging RPE

    grouped_df = (
        df.groupby([date_col, selected_group])
        .agg({
            selected_metric: "sum",
            "exercise": "sum"  # used only for RPE
        })
        .reset_index()
        .rename(columns={
            date_col: "date",
            selected_group: "group_label"
        })
    )

    if selected_metric == "sum_rpe":
        grouped_df["metric_value"] = grouped_df[selected_metric] / grouped_df["exercise"]
    else:
        grouped_df["metric_value"] = grouped_df[selected_metric]

    # --- Chart ---
    st.markdown(f"### 📈 {selected_metric_label} Over Time ({date_grouping})")
    chart = alt.Chart(grouped_df).mark_line(point=True).encode(
        x="date:T",
        y=alt.Y("metric_value:Q", title=selected_metric_label),
        color="group_label:N",
        tooltip=["date:T", "group_label:N", "metric_value:Q"]
    ).properties(height=450)

    st.altair_chart(chart, use_container_width=True)

    # --- Raw Data ---
    with st.expander("🔍 Show Raw Aggregated Data"):
        st.dataframe(grouped_df)

    if st.button("🧠 Get Performance Insights"):
        with st.spinner("Generating insights using OpenAI..."):
            import json

            # Prepare prompt
            focus_context = grouped_df.copy()
            full_context = df.copy()

            # Convert timestamps to strings for JSON serialization
            for _df in [focus_context, full_context]:
                for col in _df.columns:
                    if pd.api.types.is_datetime64_any_dtype(_df[col]):
                        _df[col] = _df[col].astype(str)

            prompt = f"""
    You are a strength coach AI analyzing training performance. Your job is to look at the user's workout trends.

    Here is the filtered view the user is analyzing:
    {focus_context.to_json(orient="records", indent=2)}

    Here is the full dataset for additional context:
    {full_context.to_json(orient="records", indent=2)}

    Provide performance insights based on the trends shown. Call out things like:
    - increases or decreases in volume or RPE
    - potential reasons (e.g. high RPE elsewhere, increased reps)
    - suggestions (e.g. increase weight, adjust intensity)
    Be specific and refer to the exercise(s) in the view.
    """

            # Get response
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            st.markdown("### 📋 Performance Insights")
            st.write(response.choices[0].message.content)
