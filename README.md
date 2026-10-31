# Earnings Call Sentiment Alpha

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://earnings-call-sentiment-snp500tech.streamlit.app)

An end-to-end NLP, SQL, and quantitative finance pipeline that tests whether earnings call sentiment predicts next-day stock returns in the S&P 500 IT sector.

## Hypothesis

> Earnings call transcripts with higher FinBERT net sentiment are positively associated with statistically significant abnormal returns in the overnight window following the call.

## Results

| Return Variable | Coefficient | P-value | R² | Significant |
|---|---|---|---|---|
| Abnormal Return (vs XLK) | 0.0790 | 0.0013 | 1.65% | ✓ Yes |
| Overnight Gap (raw) | 0.0771 | 0.0029 | 1.43% | ✓ Yes |
| Next Day Return (full day) | 0.0488 | 0.0938 | 0.45% | ~ Marginal |

**The hypothesis is supported.** Higher sentiment earnings calls are associated with significantly higher abnormal returns in the overnight window. The signal weakens over the full trading day, consistent with rapid market incorporation of sentiment information at the open before intraday noise dilutes the effect.

T-test results confirm the OLS finding: high sentiment calls averaged +0.83% abnormal return vs -0.74% for low sentiment calls, a gap of 1.57 percentage points (p = 0.0003).

The regression was reproduced independently inside PostgreSQL using `regr_slope`, which matches the statsmodels coefficient.

## Data

**Transcripts:** 643 earnings call transcripts scraped from [earningscall.biz](https://earningscall.biz) across 54 S&P 500 IT sector companies, 2022 to 2024

**Prices:** Daily OHLCV data from [Tiingo API](https://tiingo.com), including XLK as the sector benchmark

**Storage:** A normalized PostgreSQL database with four related tables

**Final dataset:** 619 earnings events after joining transcripts with price data

## Methodology

### 1. Data Collection
Scraped full earnings call transcripts (prepared remarks and Q&A) using BeautifulSoup and pulled daily adjusted price data from Tiingo for all 54 tickers plus XLK.

### 2. Transcript Cleaning
Five-layer cleaning pipeline applied before FinBERT scoring:
1. Unicode normalisation
2. Speaker label removal
3. Boilerplate removal (safe harbour disclaimers, operator instructions, pleasantries)
4. Sentence-level cleaning (annotations, inaudible markers, whitespace)
5. Low signal sentence filtering (fragments, pure number sentences, pleasantries)

### 3. Sentiment Scoring
Model: [ProsusAI/FinBERT](https://huggingface.co/ProsusAI/finbert)

Transcripts split into sentences using NLTK, each scored individually to handle FinBERT's 512 token limit. Sentence-level scores aggregated into a single net_sentiment score per transcript (avg_positive minus avg_negative).

### 4. Database
All data is loaded into PostgreSQL using a normalized schema:

| Table | Contents | Key |
|---|---|---|
| securities | One row per stock, plus the XLK benchmark | ticker |
| daily_prices | One row per ticker per trading day | ticker + price_date |
| transcripts | One row per earnings call | transcript_id (unique on ticker + call_date) |
| sentiment_scores | FinBERT scores for each transcript | transcript_id |

Foreign keys link every price, transcript, and score to a known security, so the database rejects data that doesn't fit. The loader uses `ON CONFLICT` upserts and a single transaction, so it can be re-run safely and never leaves the database half loaded.

### 5. Return Metrics
Returns are calculated in a SQL view (`earnings_events`). The `LEAD()` window function pairs each trading day with the next one. Because the price table only contains days the market was open, this handles weekends and market holidays automatically.

For each earnings call date:
- overnight_gap = (next day open minus same day close) / same day close
- intraday_return = (next day close minus next day open) / next day open
- next_day_return = (next day close minus same day close) / same day close
- abnormal_return = overnight_gap minus XLK overnight_gap

The SQL view was validated against the original Python implementation: all 619 rows matched, with differences below 0.00001.

### 6. Event Study
OLS regression of each return variable on net_sentiment and an independent samples t-test comparing high vs low sentiment groups (split at median). Primary variable: abnormal_return using XLK as sector benchmark. Additional SQL analysis covers sentiment quintiles, per-company summaries, and quarter-over-quarter sentiment changes.

## Benchmark Choice

XLK (Technology Select Sector SPDR) was used as the market benchmark rather than SPY. Since the study universe is confined to the S&P 500 IT sector, subtracting XLK's overnight gap removes sector-wide systematic movements and isolates company-specific reactions to individual earnings calls.

## Limitations

R-squared values are low (1.65% for abnormal return), reflecting the complexity of equity markets and expected for this type of study.

Some opening boilerplate survives in a small number of transcripts due to inconsistent formatting across companies. The estimated dilution effect on sentiment scores is negligible.

Results are specific to the S&P 500 IT sector, 2022 to 2024, and may not generalise to other sectors or time periods.

The 2022 rate hike cycle may confound results in that year specifically.

## Project Structure

```
earnings-call-sentiment-alpha/
│
├── app/
│   └── dashboard.py
│
├── config/
│   └── tickers.json
│
├── data/
│   ├── raw_data/
│   │   ├── cets/
│   │   └── returns_raw/
│   └── processed_data/
│       ├── cets/
│       ├── sentiment/
│       └── master.csv
│
├── sql/
│   ├── 01_schema.sql
│   ├── 02_views.sql
│   └── 03_analysis.sql
│
├── src/
│   ├── cet-scraper.py
│   ├── stock-returns.py
│   ├── ds_cleaner.py
│   ├── sentiment.py
│   ├── db.py
│   ├── load_db.py
│   ├── validate_sql.py
│   ├── export_master.py
│   └── event_study.py
│
├── DECISIONS.md
├── requirements.txt
└── README.md
```

## How to Run Locally

**1. Clone the repo**

```bash
git clone https://github.com/YOUR_USERNAME/earnings-call-sentiment-alpha.git
cd earnings-call-sentiment-alpha
```

**2. Create a virtual environment and install dependencies**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Run the dashboard**

```bash
streamlit run app/dashboard.py
```

**4. Set up PostgreSQL** (needed to re-run the pipeline)

```bash
brew install postgresql@17
brew services start postgresql@17
createdb earnings_alpha
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/earnings_alpha
TIINGO_TOKEN=your_tiingo_key
```

**5. Re-run the full pipeline** (optional)

```bash
python src/cet-scraper.py
python src/stock-returns.py
python src/ds_cleaner.py
python src/sentiment.py

psql -d earnings_alpha -f sql/01_schema.sql
python src/load_db.py
psql -d earnings_alpha -f sql/02_views.sql
python src/validate_sql.py

psql -d earnings_alpha -f sql/03_analysis.sql
python src/event_study.py
python src/export_master.py
```

API keys required: [Tiingo](https://tiingo.com) (free tier)

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.11+, SQL |
| Database | PostgreSQL, psycopg, SQLAlchemy |
| NLP | FinBERT (HuggingFace Transformers), NLTK |
| Data Collection | BeautifulSoup, Requests, Tiingo API |
| Data Processing | pandas, NumPy |
| Statistics | statsmodels, scipy |
| Visualisation | Streamlit, Plotly |
| Finance | pandas_market_calendars |

## Future Work

Host the database on a managed PostgreSQL service so the live dashboard queries it directly.

Have the scraper and sentiment scripts write straight to the database instead of JSON files.

Extend to additional S&P 500 sectors for cross-sector comparison.

Speaker-level sentiment scoring (CEO vs CFO prepared remarks vs Q&A).

Fama-French 3-factor model for more rigorous abnormal return calculation.

Intraday return analysis using higher frequency price data.

## Methodology Log

See [DECISIONS.md](DECISIONS.md) for a detailed log of data source decisions, methodology choices, problems encountered, and solutions implemented throughout the project.

*Built by David Loh · [LinkedIn](https://linkedin.com/in/YOUR_PROFILE) · [Live Dashboard](https://earnings-call-sentiment-snp500tech.streamlit.app)*
