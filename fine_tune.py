import streamlit as st
import pandas as pd
import json
from pathlib import Path

# Load dataset
csv_path = "env/analysis_output.csv"
try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    st.error("Workout data not found. Please make sure 'env/analysis_output.csv' exists.")
    st.stop()

# Ensure date column is parsed
for col in ["week_start", "month_start"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col])

# Add exercise count filter
exercise_counts = df["exercise_name"].value_counts()
valid_exercises = exercise_counts[exercise_counts >= 25].index.tolist()
df = df[df["exercise_name"].isin(valid_exercises)]

# Select target exercise
exercise = st.selectbox("Select an exercise to annotate", sorted(valid_exercises))

# Filtered and full views
filtered_df = df[df["exercise_name"] == exercise]
full_df = df.copy()

# Display preview
st.subheader(f"Filtered View: {exercise}")
st.dataframe(filtered_df)

st.subheader("Full Dataset (Context)")
with st.expander("View full data"):
    st.dataframe(full_df)

# Input response
st.subheader("✍️ Your Ideal Insight")
ideal_response = st.text_area("Write the ideal OpenAI response for this exercise trend:", height=200)

# Save entry
if st.button("✅ Save Example to JSONL"):
    # Convert timestamps to string for JSON
    for df_ in [filtered_df, full_df]:
        for col in df_.columns:
            if pd.api.types.is_datetime64_any_dtype(df_[col]):
                df_[col] = df_[col].astype(str)

    entry = {
        "messages": [
            {
                "role": "user",
                "content": f"""
You are a strength coach AI analyzing training performance. Your job is to look at the user's workout trends.

Here is the filtered view the user is analyzing:
{filtered_df.to_json(orient='records', indent=2)}

Here is the full dataset for additional context:
{full_df.to_json(orient='records', indent=2)}

Provide performance insights based on the trends shown. Call out things like:
- increases or decreases in volume or RPE
- potential reasons (e.g. high RPE elsewhere, increased reps)
- suggestions (e.g. increase weight, adjust intensity)
Be specific and refer to the exercise(s) in the view.
"""
            },
            {
                "role": "assistant",
                "content": ideal_response.strip()
            }
        ]
    }

    # Save to .jsonl file
    out_path = Path("env/fine_tune_dataset.jsonl")
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    st.success("✅ Example saved to fine_tune_dataset.jsonl")
