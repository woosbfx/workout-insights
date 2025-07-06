import duckdb
import pandas as pd
import os
from openai import OpenAI
import json
from dotenv import load_dotenv
load_dotenv()

print("✅ Environment variables loaded.")
client = OpenAI()  # Automatically uses OPENAI_API_KEY from env

csv_path = "env/strong.csv"
print(f"📂 Loading CSV from {csv_path}...")

# Step 1: Load and cast data with DuckDB
query = f"""
SELECT 
    "Date" AS workout_date
  , "Workout Name" AS workout_name
  , "Exercise Name" AS exercise_name
  , CAST("Weight" AS DOUBLE) AS weight
  , CAST("Reps" AS INT) AS reps
  , CAST(RPE AS DOUBLE) AS rpe
  , CAST("Set Order" AS INT) AS set_order
  , CAST("Weight" AS DOUBLE) * CAST("Reps" AS INT) AS volume
FROM read_csv_auto('{csv_path}')
WHERE TRUE
  AND "Weight" IS NOT NULL
  AND "Reps" IS NOT NULL
  AND TRY_CAST("Set Order" AS INT) IS NOT NULL
"""

print("🦆 Executing DuckDB query to load raw data...")
df = duckdb.query(query).to_df()
print(f"✅ Loaded {len(df):,} rows.")

# Step 3: Convert date for sorting
print("📆 Converting 'workout_date' column to datetime...")
df["workout_date"] = pd.to_datetime(df["workout_date"])

# Step 4: Sort for imputation logic
print("🔃 Sorting data by exercise, weight, reps, and date...")
df = df.sort_values(by=["exercise_name", "weight", "reps", "workout_date"])

# Step 5: Impute missing RPE
print("🔎 Imputing missing RPE values...")
df["rpe_imputed"] = df.groupby(
    ["exercise_name", "weight", "reps"]
)["rpe"].ffill()

df["rpe_imputed"] = df.groupby("workout_date")["rpe_imputed"].transform(
    lambda x: x.ffill().bfill()
)

df["rpe_imputed"] = df["rpe_imputed"].fillna(7.0)
df["rpe_was_imputed"] = df["rpe"].isna()
df["rpe"] = df["rpe_imputed"]
df.drop(columns=["rpe_imputed"], inplace=True)
print("✅ RPE imputation complete.")

# Step 5.5: Generate body part labels via OpenAI
print("🧠 Calling OpenAI to classify exercises by body part...")

unique_exercises = df["exercise_name"].dropna().unique().tolist()
print(f"🗂 Found {len(unique_exercises)} unique exercises to classify.")

rules = """
Use only the following categories: Chest, Back, Legs, Arms, Shoulders, Core.

Rules:
- Any exercise with "deadlift" should be classified as Legs
- Any exercise with "leg extension" should be Legs
- "Cable Pull Through" should be Legs
"""

exercise_list = "\n- " + "\n- ".join(unique_exercises)
prompt = f"""
Return a JSON mapping each of the following exercise names to their primary body part.

{rules}

Exercises:
{exercise_list}

Return format:
{{ "Exercise Name": "Body Part", ... }}
"""

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=0
)

body_part_map = json.loads(response.choices[0].message.content)

with open("env/body_part_map.json", "w") as f:
    json.dump(body_part_map, f, indent=2)

df["body_part"] = df["exercise_name"].map(body_part_map)
print("✅ Body part labels mapped.")

# Step 5.6: Map to upper/lower regions
print("🔍 Mapping body part to body region (Upper/Lower)...")

region_map = {
    "Chest": "Upper",
    "Back": "Upper",
    "Arms": "Upper",
    "Shoulders": "Upper",
    "Core": "Upper",
    "Legs": "Lower"
}
df["body_region"] = df["body_part"].map(region_map)
print("✅ Body region classification added.")

# Step 5.7: Add week and month grouping columns
print("📅 Creating week_start and month_start columns...")
df["week_start"] = df["workout_date"].dt.to_period("W").dt.start_time
df["month_start"] = df["workout_date"].dt.to_period("M").dt.start_time
print("✅ Temporal columns added.")

# Step 6: Register with DuckDB
print("🦆 Registering final DataFrame to DuckDB for analysis...")
con = duckdb.connect()
con.register("final_lifts", df)

analysis_query = """
  SELECT
    week_start
    , month_start
    , body_part
    , workout_name
    , exercise_name
    , 1 AS exercise
    , sum(volume) AS total_volume
    , sum(reps) AS total_reps
    , sum(rpe) AS sum_rpe
  FROM final_lifts
    GROUP BY 1, 2, 3, 4, 5, 6
"""

print("📊 Running aggregation query...")
results = con.execute(analysis_query).fetchdf()
print(f"✅ Aggregation complete: {len(results):,} rows in result set.")

# Step 8: Export results
output_path = "env/analysis_output.csv"
results.to_csv(output_path, index=False)
print(f"💾 Results exported to: {output_path}")
