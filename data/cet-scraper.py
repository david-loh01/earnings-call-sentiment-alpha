from bs4 import BeautifulSoup
import requests
import json


url = 'https://earningscall.biz/e/nasdaq/s/msft/y/2026/q/q1'
response = requests.get(url)

#ensure webpage loaded successfully, then "get" transcript.
if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup.select("p.call-text, div.speaker-name, div.designation, p.text-date"):
        print(tag.get_text(strip=True))
else:
    print(f"failed to load. \n status code: {response.status_code}")


#Find ticker symbol
script_tags = soup.find_all("script", {"type": "application/ld+json"})

data = None
for tag in script_tags:
    parsed = json.loads(tag.string)
    if "company" in parsed:
        data = parsed
        break

ticker = data["company"]["tickerSymbol"].split()[-1]
print(f"\nTICKER SYMBOL: {ticker}")

