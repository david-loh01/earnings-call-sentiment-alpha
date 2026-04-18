import pandas as pd
import json
from pathlib import Path

#----pull S&P 500 holdings list----
url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
df = pd.read_csv(url)

print(df.columns.to_list())
#----filter for Information Technology Sector----
infotech_df = df[
    (df["GICS Sector"] == "Information Technology"),
    (df["Date added"] < "2021-01-01")
]

#----build ticker list in correct format----
tickers = [
    {
        "ticker": row["Symbol"],
        "name": row["Security"],
        "exchange": "nasdaq"
    }
    for _, row in infotech_df.iterrows()
]

#----save to config----
Path(".").mkdir(exist_ok=True)
with open("./tickers.json", "w") as f:
    json.dump({"tickers": tickers}, f, indent=2)

print(f"Saved {len(tickers)} IT sector tickers")