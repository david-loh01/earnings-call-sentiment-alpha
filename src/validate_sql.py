import pandas as pd
from pathlib import Path

from db import get_engine

# ----Compare the SQL view with the master.csv that build_dataset.py made----
ROOT     = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "processed_data" / "master.csv"

sql_df = pd.read_sql("SELECT * FROM earnings_events", get_engine())
csv_df = pd.read_csv(CSV_PATH)

sql_df["date"] = pd.to_datetime(sql_df["date"])
csv_df["date"] = pd.to_datetime(csv_df["date"])

print(f"rows in SQL view:   {len(sql_df)}")
print(f"rows in master.csv: {len(csv_df)}")

merged = sql_df.merge(csv_df, on=["ticker", "date"], how="outer",
                      suffixes=("_sql", "_csv"), indicator=True)

only_sql = merged[merged["_merge"] == "left_only"]
only_csv = merged[merged["_merge"] == "right_only"]
print(f"only in SQL:        {len(only_sql)}")
print(f"only in CSV:        {len(only_csv)}")

both = merged[merged["_merge"] == "both"]
for col in ["net_sentiment", "overnight_gap", "intraday_return",
            "next_day_return", "xlk_overnight_gap", "abnormal_return"]:
    max_diff = (both[f"{col}_sql"] - both[f"{col}_csv"]).abs().max()
    status = "OK" if max_diff < 1e-5 else "MISMATCH"
    print(f"{col:<18} max difference = {max_diff:.2e}  {status}")
