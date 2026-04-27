import requests
import json
import time
import random
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from itertools import product

# ----configure the out dir----
ROOT = Path(__file__).resolve().parent.parent
quarters_list = ["q1", "q2", "q3", "q4"]
year_list = ["2022", "2023", "2024"]

# ----Create list of ticker symbols and exchange map----
with open(ROOT / "config" / "tickers.json", "r") as f:
    data = json.load(f)["tickers"]
    ticker_list = [company["ticker"] for company in data]
    exchange_map = {company["ticker"]: company["exchange"] for company in data}

# ----Build set of already scraped ticker/year/quarter combinations----
out_directory = ROOT / "data" / "raw_data" / "cets"
out_directory.mkdir(parents=True, exist_ok=True)

already_scraped = set()
for f in out_directory.glob("*.json"):
    with open(f) as file:
        try:
            saved = json.load(file)
            key = (saved["ticker"], saved.get("year", ""), saved.get("quarter", "").lower())
            already_scraped.add(key)
        except:
            pass

# ----Save function----
def save_cet(ticker: str, date: str, data: dict):
    out_directory = ROOT / "data" / "raw_data" / "cets"
    out_directory.mkdir(parents=True, exist_ok=True)

    path = out_directory / f"{ticker}_{date}.json"

    if path.exists():
        print(f"skipping {path}")
        return

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"wrote: {path}")

# ----Scrape function----
def scrape_transcript(ticker: str, year: str, quarter: str) -> dict | None:
    exchange = exchange_map.get(ticker, "nasdaq")
    url = f"https://earningscall.biz/e/{exchange}/s/{ticker.lower()}/y/{year}/q/{quarter}"

    response = requests.get(url)

    if response.status_code != 200:
        print(f"  failed ({response.status_code}): {url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # ----Get ticker symbol----
    script_tags = soup.find_all("script", {"type": "application/ld+json"})
    data = None
    for tag in script_tags:
        parsed = json.loads(tag.string)
        if "company" in parsed:
            data = parsed
            break

    if not data:
        print(f"  no company data found: {url}")
        return None

    ticker = data["company"]["tickerSymbol"].split()[-1]

    # ----Get date----
    date_tag = soup.select_one("p.text-date")
    if not date_tag:
        print(f"  no date found: {url}")
        return None

    date = date_tag.get_text(strip=True)
    safe_date = datetime.strptime(date, "%m/%d/%Y").strftime("%m-%d-%Y")

    # ----Get transcript----
    transcript_text = "\n".join(
        tag.get_text(strip=True)
        for tag in soup.select("p.call-text, div.speaker-name, div.designation")
    )

    if not transcript_text:
        print(f"  no transcript text found: {url}")
        return None

    # ----Create payload----
    payload = {
        "ticker": ticker,
        "date": safe_date,
        "year": year,
        "quarter": quarter,
        "source_url": url,
        "transcript": transcript_text,
    }

    return payload

# ----Retry wrapper----
def scrape_with_retry(ticker: str, year: str, quarter: str, max_retries: int = 3) -> dict | None:
    for attempt in range(max_retries):
        result = scrape_transcript(ticker, year, quarter)
        if result:
            return result
        wait = random.uniform(10, 20)
        print(f"  retrying in {wait:.0f}s... (attempt {attempt + 1}/{max_retries})")
        time.sleep(wait)
    return None

# ----Main loop----
total = 0
failed = 0

for ticker, year, quarter in product(ticker_list, year_list, quarters_list):

    # ----Check if already scraped before making any request----
    key = (ticker, year, quarter)
    if key in already_scraped:
        print(f"{ticker} {year} {quarter.upper()} → skipping — already exists")
        continue

    print(f"{ticker} {year} {quarter.upper()}", end=" → ")

    payload = scrape_with_retry(ticker, year, quarter)

    if payload:
        save_cet(payload["ticker"], payload["date"], payload)
        already_scraped.add(key)  # add to set so we don't retry in same session
        total += 1
    else:
        failed += 1

    time.sleep(random.uniform(2, 5))

print(f"\nDone. saved: {total} | failed: {failed}")