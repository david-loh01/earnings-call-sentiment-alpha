import requests
import json
from bs4 import BeautifulSoup
from pathlib import Path

url = 'https://earningscall.biz/e/nasdaq/s/msft/y/2026/q/q1'
response = requests.get(url)

#----ensure webpage loaded successfully----
if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
else:
    print(f"failed to load. \n status code: {response.status_code}")

#----Get ticker symbol----
script_tags = soup.find_all("script", {"type": "application/ld+json"})

data = None
for tag in script_tags:
    parsed = json.loads(tag.string)
    if "company" in parsed:
        data = parsed
        break

ticker = data["company"]["tickerSymbol"].split()[-1]
print(f"\nTICKER SYMBOL: {ticker}")

#----Get date----
#date_tag = soup.find_all("p.text-date")
#print(f"DaTe: {date_tag}")
for date_tag in soup.select("p.text-date"):#if date_tag else "unknown"
    date = date_tag.get_text(strip=True)
    safe_date = date.replace("/", "-")
print(f"\nDATE: {safe_date}")

#----Get transcript----
transcript_text = "\n".join(
    tag.get_text(strip=True) for tag in soup.select("p.call-text, div.speaker-name, div.designation")
)

#----Create Payload----
payload = {
    "ticker": ticker,
    "date": safe_date,
    "source_url": url,
    "transcript": transcript_text,
}

#----Creating separate transcript files for each CET----
def save_cet(ticker: str, date: str, data: dict):
    out_directory = Path("cets")
    out_directory.mkdir(parents=True, exist_ok=True)

    path = out_directory / f"{ticker}_{date}.json"

    #Make sure we don't overwrite existing files
    if path.exists():
        print(f"skipping {path}")
        return

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"wrote: {path}")

#----Call "save_cet"----
save_cet(ticker, safe_date, payload)
