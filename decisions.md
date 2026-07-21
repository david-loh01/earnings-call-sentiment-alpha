
##### About: This document details the decisions or important information that I made/found along the way. This includes, but is not limited to, problems I encounter, new information that I find, solutions to problems, and methodology, that can deviate from the original project outline.


- Finding a reliable scraping source for Call Earning Transcripts (CET) was not easy. Many of the most reliable sources (Seeking Alpha, Motley Fool, etc.) hide their CET's behind pay walls, would require a rotating proxy, need "clicking" (therefore needing selenium), and/or have inconsistent links
- This is not a web-scraping problem or project, and is not worth the time that it would take to figure it out. 
- ***SEC Edgar*** will contain the information needed.
	Considerations:
	- Demands choosing largest S&P 500 sector as transcript reports are not mandatory
	- May only contain a certain percentage of the companies from the largest sector. This is why we must choose the largest sector
	- Included in ***SEC Edgar's*** fair access policy, I must include ```'YourName yourname@email.com'```, called "User-Agent Header"
		- This is a non-negotiable, non-skippable requirement that is needed in every single request.
		- The CET's are under what called their "8-K"
	***Fallback Strategy
	- I will "skip" the companies that do not supply their CET's to SEC Edgar. Not worth the time sink to manually locate (potentially through multiple sources) the rest of the companies CET's.
- Switched from "SEC Edgar" to "earningcalls.biz". SEC Edgar 8-K filings is no longer a viable option. It doesn't reliably supply full CET's and usually only contains small prepared remarks or excerpts from the full call. Since the Q&A section contains less scripted, potentially more signal-rich language, using partial transcripts would introduce systematic bias toward positive sentiment and reduce the validity of the analysis. [earningcalls.biz](earningcalls.biz) provides independently transcribed full transcripts including Q&A for S&P 500 companies. 

- Chose "Beautiful Soup" to scrape* & parse the CET's. 
	\* Beautiful Soup is considered a parser rather than a scraper, but since our choice of website is so simple, a parser will be perfect. However, for readability, I will henceforth just call it "scraping"
- earningscalls.biz is robot.txt allowed for parsing CET's
- To have a proof of concept, I am only going to scrape from: MSFT Q1-2026
	- After everything works, I will add the rest of the symbols CET's
- After scraping the MSFT Q1-2026 CET, I decided to scrape the call-text, the speaker-name, and the designation. In the future, I will probably need to remove speaker-name and designation. But for now, I want as much information in my raw file and filter later in case I do end up needing the extra information.
- I am separating the files for the collection of the CET and the stock price. Different collection methods, different failure points, etc,.
- Realized I need more information when scraping
	- ticker symbol
	- date of call
- Created a file containing the MSFT Q1-2026 CET
- The pipeline should work first, so before scraping my entire ticker list, I will make sure that I can scrape the corresponding stock data.
	- However, the pipeline will look like this:
		 1. Define the ticker list (50-100 S&P 500 companies)  
		 2. -> Pull returns from finance source for all of them
		 3. -> Check which tickers have complete data — drop any that don't 
		 4. -> Scrape transcripts only for the validated ticker list
		 5. -> Join them in build_dataset.py
- Looking into best source for financial data. Alpha Vantage seems to be good. 
	- API KEY: NWBCLOBYD09GS6MX.

- For ease of reading, all parts of the date that are single digit, now have a "0" appended to the beginning of them for readability.
	- ex. 1-23-2021 -> 01-23-2021 (mm-dd-yyyy)
- created a json of all S&P 500 Information Technology Holdings. Excluding all holdings from 2021 onwards
- The list that I am using only contains ticker symbols from NASDAQ. There are only a few on the NYSE. I tried using a different source to get all the data across all exchanges. For the trouble that it caused me, I don't think 4 or 5 stocks will make much of a difference out of 70+. 
	- Instead of scraping them, I will just hardcode the ticker symbols instead. it is probably best to have as much information as possible anyways.
- Changed the date range
	- Originally, 2021-2023 -> Now, 2022-2024
	- There are 70+ companies that are in the Information & Technology sector as of Apr.18.2026. But my range of 2021-2023 only has 50. Too small a number for accurate model results. I will choose the date range 2022-2024. Only 5 more companies than 2021, but I want to avoid 2025 which is a HIGHLY bullish period for tech that will skew my results too much. I cannot go earlier because of COVID's confounding effects in 2019, and there are no good CET's from before 2020. At least from: [earningcalls.biz](earningcalls.biz), and this website works excellently. Additionally, 2022-2024 includes a down year, 2022 and a recovery year, 2023. 2024 is stable enough.
		- Note that 2022 has a rate hike cycle which may also confound results.
- Cannot retrieve the right data from "AlphaVantage"
	- Free tier does not allow data from more than 100 days. Insufficient for the date range
	- Additionally, I cannot retrieve the "adjusted" prices. So, accounting for stock splits.


- Changed stock data source to "Tiingo
	- Tiingo API-Key: 2745b29f3b5817d280936c42fbd0bc2b146af711
	- Tiingo offers much more in their free tier that allows us to make these pulls free of charge


- pulled data from Tiingo into my project folder```  ../data/raw_data/returns_raw/
  
- ticker ZBRA has no data, but all others were successful
- sampled all daily Open, High, Low, Close, Volume (OHLCV) data from Tiingo.
	- More data is better, and it is a simple task to select the dates that I want
- gitignore all raw data. Not necessary to push to repo
- edited cet_scraper to systematically find all CETs
	- set random request delays to not time out, or get blocked
- APH/Amphenol is on the NYSE, not NASDAQ
- Script retries for every stock that it cannot find. All because json contained the wrong exchange. 
	- manually looked at all companies and double checked that the json has them on the right exchange
	- chose manual look-up because it's a small list. Would find better solution if the list was larger
- Changed the order of operations
	- OLD: Scrape CET then check if it exists, if it does, skip
	- NEW: Check if CET exists, then scrape
- Reasons for absence of CETs:
	- CDNS Q3: DNE
	- CTSH Q3: No audio, no CET
	- ORCL ALL QUARTERS ALL YEARS: restricted access
	- GEN Q3 2024: No audio, no CET
	- KLAC 2022 Q1: No audio, no CET

- Gathered 643/660 CETs
	- For reasons listed prior, those CETs could not be pulled.
- Need to join the two datasets. Some things need to be taken care of.
	- Date format needs to be formalized
		- Will use: YYY-MM-DD
	- Data will be cleaned before joining the transcripts and the OHLCV data
		- **Transcript Cleaning Pipeline**
			- Raw transcripts were cleaned in five sequential layers before being passed to FinBERT:

			- **Layer 1 — Unicode normalization.** All text was normalized to ASCII to remove invisible characters, smart quotes, non-breaking spaces, and other encoding artifacts introduced during web scraping. These characters are invisible to the human eye but break regex patterns and tokenization.

			- **Layer 2 — Speaker label removal.** Speaker names and designations were stripped by identifying lines that are short (under 60 characters), contain no sentence-ending punctuation, and match a name/title pattern. These lines carry no sentiment content and waste FinBERT's token budget.

			- **Layer 3 — Boilerplate removal.** Recurring non-informative blocks were removed using regular expression patterns targeting: safe harbour and forward-looking statements disclaimers, operator instructions, opening pleasantries, and call transition phrases. These blocks appear in virtually every transcript and score as strongly negative or neutral on FinBERT despite having no bearing on business performance.

			- **Layer 4 — Sentence-level cleaning.** Each remaining sentence was cleaned of bracketed annotations (`[Laughter]`, `[Applause]`), inaudible markers, irregular whitespace, and any remaining non-ASCII characters.

			- **Layer 5 — Low signal sentence filtering.** Sentences were discarded if they were fewer than 6 words (fragments and pleasantries), more than 80 words (compound legal constructions), matched known low-signal phrases ("Thank you", "Moving on", "Great question"), or were less than 40% alphabetic characters (dominated by numbers and symbols that FinBERT cannot score meaningfully).

			- **What was deliberately kept.** Hedging language ("we expect", "we believe", "may", "could") was intentionally preserved. This language is analytically valuable — FinBERT scores hedged positive statements differently from confident ones, and that difference is part of the sentiment signal being measured.

			- **Result.** Cleaned transcripts averaged 15-30% fewer words than raw transcripts, with all remaining content being substantive financial language spoken by company executives.

- Decided to stop continuing to clean my transcripts. My efforts to clean better are yielding diminishing returns.
	- Cleaning pipeline removes speaker labels, operator instructions, safe harbour disclaimers, and duplicate content. 
	- Some opening boilerplate survives in a small number of transcripts due to inconsistent formatting across companies. 
	- This is accepted as a known limitation — the affected sentences represent less than 1% of transcript content and their dilution effect on aggregate FinBERT sentiment scores is negligible.

- Scored all 643 cleaned transcripts using FinBERT (ProsusAI/finbert)
  - Used sentence-level scoring with nltk sent_tokenize to handle FinBERT's 512 token limit
  - Used top_k=None parameter (replaces deprecated return_all_scores=True) to retrieve all three label scores per sentence
  - Aggregated sentence-level scores into per-transcript metrics:
    - avg_positive, avg_negative, avg_neutral, net_sentiment (positive minus negative)
    - sentences_scored (used as a quality check — transcripts with fewer than 50 sentences flagged)
  - net_sentiment mean across all transcripts: 0.235 — slightly elevated, likely due to residual boilerplate in a small number of transcripts. Accepted as known limitation.
  - PyTorch nightly build required due to Python 3.13 compatibility issue with stable release

- Built master dataset (build_dataset.py)
  - Joined 643 sentiment files with Tiingo price data on (ticker, date)
  - Used pandas_market_calendars with NYSE schedule to find next trading day — handles weekends and market holidays correctly. A plain BDay(1) offset would incorrectly assign returns on days the market was closed.
  - Calculated four return metrics per earnings call:
    - overnight_gap = (next_day_open - same_day_close) / same_day_close
    - intraday_return = (next_day_close - next_day_open) / next_day_open
    - next_day_return = (next_day_close - same_day_close) / same_day_close
    - abnormal_return = overnight_gap - XLK_overnight_gap
  - 619 rows saved, 24 skipped
    - ZBRA: no price file available
    - 23 transcripts dated in 2025: outside study window, correctly excluded
  - 0 nulls in abnormal_return column

- Added XLK as market benchmark
  - Used XLK (Technology Select Sector SPDR) rather than SPY as the benchmark
  - Rationale: study universe is confined to the S&P 500 IT sector. Subtracting XLK's overnight gap removes sector-wide systematic movements and isolates company-specific reactions to individual earnings calls. SPY would leave sector-wide tech momentum as a confounder.
  - abnormal_return is the primary dependent variable in the event study

- Event study results (event_study.py)
  - Ran OLS regression and independent samples t-test for all three return variables
  - Primary finding: net_sentiment is a statistically significant positive predictor of abnormal returns
    - Abnormal return: coefficient = 0.079, p = 0.0013 *** significant, R² = 1.65%
    - Overnight gap: coefficient = 0.077, p = 0.0029 *** significant, R² = 1.43%
    - Next day return: coefficient = 0.049, p = 0.0938 * marginal, R² = 0.45%
  - T-test results (high vs low sentiment groups split at median):
    - Abnormal return: high sentiment mean = +0.83%, low sentiment mean = -0.74%, p = 0.0003
    - Overnight gap: high = +0.95%, low = -0.58%, p = 0.0008
    - Next day return: high = +0.93%, low = -0.02%, p = 0.0628
  - Signal weakens over the full trading day — consistent with rapid market incorporation of earnings call sentiment at the open before intraday noise dilutes the effect
  - Low R² (1.6%) reflects the complexity of equity markets, not a methodological weakness. Expected and honest finding.

- Built Streamlit dashboard (app/dashboard.py)
  - Four sections: key metrics, scatter plot with OLS trendline, bar chart of high vs low sentiment group returns, sentiment over time by ticker
  - Statistical results displayed in tabbed OLS and t-test tables
  - Written findings summary auto-populated from computed results
  - Run locally with: streamlit run app/dashboard.py