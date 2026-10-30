-- ============================================================
-- 02_views.sql
-- Replaces build_dataset.py. The join and the return
-- calculations now live in the database as views.
--
-- Run with:  psql -d earnings_alpha -f sql/02_views.sql
-- ============================================================

DROP VIEW IF EXISTS earnings_events, price_windows CASCADE;


-- ----Step 1: put each trading day next to the trading day after it----
-- daily_prices only contains days the market was open, so "the next
-- row for this ticker" is the next trading day. This replaces
-- pandas_market_calendars: weekends and holidays are never in the table.
CREATE VIEW price_windows AS
SELECT
    ticker,
    price_date,
    adj_close                AS same_day_close,
    LEAD(price_date) OVER w  AS next_trading_day,
    LEAD(adj_open)   OVER w  AS next_day_open,
    LEAD(adj_close)  OVER w  AS next_day_close
FROM daily_prices
WINDOW w AS (PARTITION BY ticker ORDER BY price_date);


-- ----Step 2: one row per earnings call with sentiment and returns----
-- Same columns as the old master.csv.
CREATE VIEW earnings_events AS
SELECT
    t.ticker,
    t.call_date                                         AS date,
    EXTRACT(YEAR FROM t.call_date)::INT                 AS year,
    'Q' || EXTRACT(QUARTER FROM t.call_date)::INT       AS quarter,

    s.net_sentiment,
    s.avg_positive,
    s.avg_negative,
    s.avg_neutral,
    s.sentences_scored,

    p.same_day_close,
    p.next_day_open,
    p.next_day_close,

    (p.next_day_open  - p.same_day_close) / p.same_day_close  AS overnight_gap,
    (p.next_day_close - p.next_day_open)  / p.next_day_open   AS intraday_return,
    (p.next_day_close - p.same_day_close) / p.same_day_close  AS next_day_return,

    (x.next_day_open  - x.same_day_close) / x.same_day_close  AS xlk_overnight_gap,

    (p.next_day_open  - p.same_day_close) / p.same_day_close
  - (x.next_day_open  - x.same_day_close) / x.same_day_close  AS abnormal_return

FROM transcripts t
JOIN sentiment_scores s
    ON s.transcript_id = t.transcript_id
JOIN price_windows p                      -- the company's prices
    ON  p.ticker     = t.ticker
    AND p.price_date = t.call_date
JOIN price_windows x                      -- XLK's prices over the same window
    ON  x.ticker           = 'XLK'
    AND x.price_date       = t.call_date
    AND x.next_trading_day = p.next_trading_day
WHERE p.next_trading_day IS NOT NULL;
