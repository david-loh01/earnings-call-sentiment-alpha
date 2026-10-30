import pandas as pd
from pathlib import Path

from db import get_engine

# ----Write the earnings_events view to master.csv for the deployed dashboard----
ROOT     = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "processed_data" / "master.csv"

df = pd.read_sql("SELECT * FROM earnings_events ORDER BY ticker, date", get_engine())
df.to_csv(OUT_PATH, index=False)

print(f"exported {len(df)} rows to {OUT_PATH}")
