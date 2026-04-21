import pandas as pd
import requests
import json
from pathlib import Path

#----pull S&P 500 holdings list----
url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
df = pd.read_csv(url)

print(df.columns.to_list())

#----filter for Information Technology Sector----
infotech_df = df[
    (df["GICS Sector"] == "Information Technology") &
    (df["Date added"] < "2022-01-01")
]

# ----NYSE tickers that need a different exchange prefix----
NYSE_TICKERS = {"ACN", "IBM", "GLW", "HPE"}

#----build ticker list in correct format----
tickers = [
    {
        "ticker": row["Symbol"],
        "name": row["Security"],
        "exchange": "nyse" if row["Symbol"] in NYSE_TICKERS else "nasdaq"    }
    for _, row in infotech_df.iterrows()
]

#----save to config----
out_path = Path(__file__).resolve().parent / "tickers.json"
with open("./tickers.json", "w") as f:
    json.dump({"tickers": tickers}, f, indent=2)

print(f"Saved {len(tickers)} IT sector tickers")