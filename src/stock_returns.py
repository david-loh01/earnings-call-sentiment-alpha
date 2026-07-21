import requests
import json
import time
from pathlib import Path

#----supply the token & set out directory----
tiingo_token = "2745b29f3b5817d280936c42fbd0bc2b146af711"
out_dir = Path(__file__).resolve().parent.parent / "data" / "raw_data" / "returns_raw"

#ohlcv = open, high, low, close, volume
#----send request to Tiingo for the parameters that we set----
def get_daily_ohlcv(ticker: str) -> list:
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    headers = {
        "Authorization": f"Token {tiingo_token}",
        "Content-Type": "application/json"
    }
    params = {
        "startDate": "2021-01-01",
        "endDate":   "2024-12-31",
        "resampleFreq": "daily"
    }
    response = requests.get(url, headers=headers, params=params)
    print(response.status_code, response.text[:200])
    return response.json()

#----define the price saving function----
def save_prices(ticker: str, ohlcv: list):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ticker}.json"

    if path.exists():
        print(f"Skipping {ticker}")
        return
    #----check Tiingo did not return an error
    if not isinstance(ohlcv, list) or len(ohlcv) == 0:
        print(f"failed - no ohlcv data returned for: {ticker}")
        return

    with open(path, "w") as f:
        json.dump(ohlcv, f, indent=2)
    print(f"successfully saved {ticker}")

#----load ticker list----
root = Path(__file__).resolve().parent.parent
with open("../config/tickers.json", 'r') as f:
    tickers = json.load(f)["tickers"]

#----retrieve prices for each ticker----
for company in tickers:
    ticker = company["ticker"]
    print(f"{ticker}", end = " → ")
    data = get_daily_ohlcv(ticker)
    save_prices(ticker, data)
    time.sleep(0.5)

# ----Pull XLK as market benchmark----
print("XLK", end=" → ")
xlk_data = get_daily_ohlcv("XLK")
save_prices("XLK", xlk_data)
