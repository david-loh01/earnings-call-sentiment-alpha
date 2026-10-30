import json
from datetime import datetime
from pathlib import Path

from db import get_connection

ROOT          = Path(__file__).resolve().parent.parent
TICKERS_PATH  = ROOT / "config" / "tickers.json"
PRICES_DIR    = ROOT / "data" / "raw_data" / "returns_raw"
CLEANED_DIR   = ROOT / "data" / "processed_data" / "cets"
SENTIMENT_DIR = ROOT / "data" / "processed_data" / "sentiment"

BENCHMARK = ("XLK", "Technology Select Sector SPDR Fund", "nysearca", True)


# ----Transcript dates were saved as MM-DD-YYYY; accept YYYY-MM-DD too----
def parse_date(date_str: str):
    for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date: {date_str}")


# ----Table 1: securities----
def load_securities(conn) -> set:
    with open(TICKERS_PATH) as f:
        companies = json.load(f)["tickers"]

    rows = [(c["ticker"], c["name"], c["exchange"], False) for c in companies]
    rows.append(BENCHMARK)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO securities (ticker, name, exchange, is_benchmark)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ticker) DO UPDATE
                SET name         = EXCLUDED.name,
                    exchange     = EXCLUDED.exchange,
                    is_benchmark = EXCLUDED.is_benchmark
            """,
            rows,
        )
    print(f"securities:       {len(rows)} rows")
    return {row[0] for row in rows}


# ----Table 2: daily_prices----
def load_prices(conn, known_tickers: set):
    total = 0
    for path in sorted(PRICES_DIR.glob("*.json")):
        ticker = path.stem
        if ticker not in known_tickers:
            print(f"  skipping prices for {ticker}: not in tickers.json")
            continue

        with open(path) as f:
            daily = json.load(f)

        rows = [
            (
                ticker,
                datetime.strptime(entry["date"][:10], "%Y-%m-%d").date(),
                entry["open"], entry["high"], entry["low"], entry["close"],
                entry["adjOpen"], entry["adjClose"], entry["volume"],
            )
            for entry in daily
        ]

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO daily_prices
                    (ticker, price_date, open, high, low, close, adj_open, adj_close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, price_date) DO NOTHING
                """,
                rows,
            )
        total += len(rows)
    print(f"daily_prices:     {total} rows")


# ----Tables 3 and 4: transcripts and sentiment_scores----
def load_transcripts_and_sentiment(conn, known_tickers: set):
    n_transcripts = n_scores = 0

    with conn.cursor() as cur:
        for path in sorted(CLEANED_DIR.glob("*.json")):
            with open(path) as f:
                cet = json.load(f)

            ticker = cet["ticker"]
            if ticker not in known_tickers:
                print(f"  skipping {path.name}: {ticker} not in tickers.json")
                continue

            call_date = parse_date(cet["date"])

            # insert (or update) the transcript and get its id back
            cur.execute(
                """
                INSERT INTO transcripts (ticker, call_date, source_url, cleaned_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ticker, call_date) DO UPDATE
                    SET source_url   = EXCLUDED.source_url,
                        cleaned_text = EXCLUDED.cleaned_text
                RETURNING transcript_id
                """,
                (ticker, call_date, cet.get("source_url"), cet["transcript"]),
            )
            transcript_id = cur.fetchone()[0]
            n_transcripts += 1

            # the matching sentiment file has the same filename
            sent_path = SENTIMENT_DIR / path.name
            if not sent_path.exists():
                print(f"  no sentiment file for {path.name}")
                continue

            with open(sent_path) as f:
                sent = json.load(f)

            cur.execute(
                """
                INSERT INTO sentiment_scores
                    (transcript_id, net_sentiment, avg_positive, avg_negative,
                     avg_neutral, sentences_scored)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (transcript_id) DO UPDATE
                    SET net_sentiment    = EXCLUDED.net_sentiment,
                        avg_positive     = EXCLUDED.avg_positive,
                        avg_negative     = EXCLUDED.avg_negative,
                        avg_neutral      = EXCLUDED.avg_neutral,
                        sentences_scored = EXCLUDED.sentences_scored
                """,
                (transcript_id, sent["net_sentiment"], sent["avg_positive"],
                 sent["avg_negative"], sent["avg_neutral"], sent["sentences_scored"]),
            )
            n_scores += 1

    print(f"transcripts:      {n_transcripts} rows")
    print(f"sentiment_scores: {n_scores} rows")


# ----Run everything in one transaction: all of it loads, or none of it does----
with get_connection() as conn:
    known_tickers = load_securities(conn)
    load_prices(conn, known_tickers)
    load_transcripts_and_sentiment(conn, known_tickers)

print("\nDone.")
