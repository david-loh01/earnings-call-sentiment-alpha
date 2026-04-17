from bs4 import BeautifulSoup
import requests


url = 'https://earningscall.biz/e/nasdaq/s/msft/y/2026/q/q1'
response = requests.get(url)

#ensure webpage loaded succesfully
if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup.select("p.call-text, div.speaker-name, div.designation"):
        print(tag.get_text(strip=True))
else:
    print(f"failed to load. \n status code: {response.status_code}")

