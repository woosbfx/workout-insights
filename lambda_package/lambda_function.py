import json
import pandas as pd
import boto3
import os

s3 = boto3.client("s3")

def lambda_handler(event, context):
    # --- Load from S3 ---
    bucket = event["bucket"]
    key = event["key"]
    local_csv_path = "/tmp/strong.csv"
    s3.download_file(bucket, key, local_csv_path)

    # --- Load CSV into pandas ---
    df = pd.read_csv(local_csv_path)

    # --- Rename and cast ---
    df = df.rename(columns={
        "Date": "workout_date",
        "Workout Name": "workout_name",
        "Exercise Name": "exercise_name",
        "Weight": "weight",
        "Reps": "reps",
        "RPE": "rpe",
        "Set Order": "set_order"
    })

    df = df[df["weight"].notna() & df["reps"].notna() & df["set_order"].notna()]
    df["volume"] = df["weight"] * df["reps"]
    df["workout_date"] = pd.to_datetime(df["workout_date"])
    df = df.sort_values(by=["exercise_name", "weight", "reps", "workout_date"])

    # --- Impute RPE ---
    df["rpe_imputed"] = df.groupby(["exercise_name", "weight", "reps"])["rpe"].ffill()
    df["rpe_imputed"] = df.groupby("workout_date")["rpe_imputed"].transform(lambda x: x.ffill().bfill())
    df["rpe_imputed"] = df["rpe_imputed"].fillna(7.0)
    df["rpe_was_imputed"] = df["rpe"].isna()
    df["rpe"] = df["rpe_imputed"]
    df.drop(columns=["rpe_imputed"], inplace=True)

    # --- Add week/month ---
    df["week_start"] = df["workout_date"].dt.to_period("W").dt.start_time
    df["month_start"] = df["workout_date"].dt.to_period("M").dt.start_time

    # --- Load body part map ---
    with open("body_part_map.json", "r") as f:
        body_part_map = json.load(f)
    df["body_part"] = df["exercise_name"].map(body_part_map)

    # --- Aggregate ---
    results = (
        df.groupby(["week_start", "month_start", "body_part", "workout_name", "exercise_name"])
        .agg(
            sets=("exercise_name", "count"),
            total_volume=("volume", "sum"),
            total_reps=("reps", "sum"),
            sum_rpe=("rpe", "sum")
        )
        .reset_index()
    )

    # --- Save to /tmp and upload ---
    output_path = "/tmp/analysis_output.csv"
    results.to_csv(output_path, index=False)

    output_key = "processed/analysis_output.csv"
    s3.upload_file(output_path, bucket, output_key)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Analysis complete", "output_key": output_key})
    }
