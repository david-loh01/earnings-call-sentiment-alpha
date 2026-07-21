import json
import pandas as pd
import pandas_market_calendars as mcal
from pathlib import Path
from datetime import datetime

ROOT          = Path(__file__).resolve().parent.parent
SENTIMENT_DIR = ROOT / "data" / "processed_data" / "sentiment"
PRICES_DIR    = ROOT / "data" / "raw_data" / "returns_raw"
OUT_PATH      = ROOT / "data" / "processed_data" / "master.csv"

nyse = mcal.get_calendar("NYSE")

# ----Get next NYSE trading day after a given date----
def get_next_trading_day(date_str: str) -> str:
    date = pd.Timestamp(date_str)
    end  = date + pd.Timedelta(days=14)
    schedule     = nyse.schedule(
        start_date=date.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d")
    )
    trading_days = mcal.date_range(schedule, frequency="1D")
    next_day = next(
        (d for d in trading_days if d.date() > date.date()),
        None
    )
    return next_day.strftime("%Y-%m-%d") if next_day else None

# ----Load Tiingo price file for a ticker and index by date----
def load_prices(ticker: str) -> dict:
    path = PRICES_DIR / f"{ticker}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        daily = json.load(f)
    return {entry["date"][:10]: entry for entry in daily}

# ----Build master dataset----
def build_dataset():
    sentiment_files = list(SENTIMENT_DIR.glob("*.json"))
    print(f"Found {len(sentiment_files)} sentiment files")

    # ----Load XLK as benchmark----
    xlk_prices = load_prices("XLK")
    if not xlk_prices:
        raise FileNotFoundError("XLK price file not found — run stock-returns.py first")
    print("XLK benchmark loaded.")

    records = []
    skipped = 0

    for path in sentiment_files:
        with open(path) as f:
            sent = json.load(f)

        ticker = sent["ticker"]

        # ----Convert MM-DD-YYYY to YYYY-MM-DD for price lookup----
        try:
            date_obj = datetime.strptime(sent["date"], "%m-%d-%Y")
            date_str = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            date_str = sent["date"]

        # ----Load matching price data----
        prices = load_prices(ticker)
        if not prices:
            print(f"  no price file found for {ticker} — skipping")
            skipped += 1
            continue

        # ----Check same day prices exist----
        if date_str not in prices:
            print(f"  no price for {ticker} on {date_str} — skipping")
            skipped += 1
            continue

        # ----Get next trading day----
        next_day = get_next_trading_day(date_str)
        if not next_day or next_day not in prices:
            print(f"  no next trading day for {ticker} after {date_str} — skipping")
            skipped += 1
            continue

        # ----Extract company prices----
        same_day   = prices[date_str]
        next_day_p = prices[next_day]

        same_day_close  = float(same_day["adjClose"])
        next_day_open   = float(next_day_p["adjOpen"])
        next_day_close  = float(next_day_p["adjClose"])

        # ----Calculate return metrics----
        overnight_gap   = (next_day_open  - same_day_close) / same_day_close
        intraday_return = (next_day_close - next_day_open)  / next_day_open
        next_day_return = (next_day_close - same_day_close) / same_day_close

        # ----Calculate abnormal return using XLK as benchmark----
        if next_day in xlk_prices and date_str in xlk_prices:
            xlk_same_day_close = float(xlk_prices[date_str]["adjClose"])
            xlk_next_day_open  = float(xlk_prices[next_day]["adjOpen"])
            xlk_overnight_gap  = (xlk_next_day_open - xlk_same_day_close) / xlk_same_day_close
            abnormal_return    = overnight_gap - xlk_overnight_gap
        else:
            xlk_overnight_gap = None
            abnormal_return   = None

        records.append({
            "ticker":            ticker,
            "date":              date_str,
            "quarter":           sent.get("quarter", ""),
            "year":              sent.get("year",    ""),
            "net_sentiment":     sent["net_sentiment"],
            "avg_positive":      sent["avg_positive"],
            "avg_negative":      sent["avg_negative"],
            "avg_neutral":       sent["avg_neutral"],
            "sentences_scored":  sent["sentences_scored"],
            "same_day_close":    round(same_day_close,   4),
            "next_day_open":     round(next_day_open,    4),
            "next_day_close":    round(next_day_close,   4),
            "overnight_gap":     round(overnight_gap,    6),
            "intraday_return":   round(intraday_return,  6),
            "next_day_return":   round(next_day_return,  6),
            "xlk_overnight_gap": round(xlk_overnight_gap, 6) if xlk_overnight_gap is not None else None,
            "abnormal_return":   round(abnormal_return,   6) if abnormal_return   is not None else None,
        })

    # ----Save master CSV----
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    # ----Derive year and quarter from date----
    df["date"]    = pd.to_datetime(df["date"])
    df["year"]    = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter.map({1:"Q1", 2:"Q2", 3:"Q3", 4:"Q4"})

    df.to_csv(OUT_PATH, index=False)

    print(f"\nDone.")
    print(f"  rows saved:   {len(df)}")
    print(f"  rows skipped: {skipped}")
    print(f"  nulls in abnormal_return: {df['abnormal_return'].isnull().sum()}")
    print(f"  output: {OUT_PATH}")

    return df

build_dataset()