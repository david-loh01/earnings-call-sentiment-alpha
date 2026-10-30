-- ============================================================
-- 03_analysis.sql
-- Analytical queries on the earnings_events view.
-- Run one at a time in psql, or all at once with:
--   psql -d earnings_alpha -f sql/03_analysis.sql
-- ============================================================


-- ----1. Coverage: how many calls per year made it into the dataset?----
SELECT year, COUNT(*) AS calls, COUNT(DISTINCT ticker) AS companies
FROM earnings_events
GROUP BY year
ORDER BY year;


-- ----2. Regression cross-check----
-- Postgres can fit a one-variable regression itself. These numbers
-- should match event_study.py (coefficient ~0.079, R-squared ~0.0165).
SELECT
    COUNT(*)                                         AS n,
    ROUND(regr_slope(abnormal_return, net_sentiment)::NUMERIC, 6)     AS slope,
    ROUND(regr_intercept(abnormal_return, net_sentiment)::NUMERIC, 6) AS intercept,
    ROUND(regr_r2(abnormal_return, net_sentiment)::NUMERIC, 6)        AS r_squared,
    ROUND(corr(abnormal_return, net_sentiment)::NUMERIC, 4)           AS correlation
FROM earnings_events;


-- ----3. Median split (the groups behind your t-test)----
-- Should match: high ~ +0.83%, low ~ -0.74%.
WITH median AS (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY net_sentiment) AS m
    FROM earnings_events
)
SELECT
    CASE WHEN e.net_sentiment > median.m THEN 'high' ELSE 'low' END   AS sentiment_group,
    COUNT(*)                                                          AS calls,
    ROUND(AVG(e.abnormal_return)::NUMERIC * 100, 3)                   AS avg_abnormal_return_pct,
    ROUND(STDDEV(e.abnormal_return)::NUMERIC * 100, 3)                AS std_pct
FROM earnings_events e
CROSS JOIN median
GROUP BY sentiment_group
ORDER BY sentiment_group;


-- ----4. Sentiment quintiles: does return rise steadily with sentiment?----
-- A real effect should climb from quintile 1 to 5, not just differ at the ends.
WITH ranked AS (
    SELECT *, NTILE(5) OVER (ORDER BY net_sentiment) AS quintile
    FROM earnings_events
)
SELECT
    quintile,
    COUNT(*)                                          AS calls,
    ROUND(MIN(net_sentiment)::NUMERIC, 3)             AS min_sentiment,
    ROUND(MAX(net_sentiment)::NUMERIC, 3)             AS max_sentiment,
    ROUND(AVG(abnormal_return)::NUMERIC * 100, 3)     AS avg_abnormal_return_pct
FROM ranked
GROUP BY quintile
ORDER BY quintile;


-- ----5. Per-company summary----
SELECT
    e.ticker,
    s.name,
    COUNT(*)                                          AS calls,
    ROUND(AVG(e.net_sentiment)::NUMERIC, 3)           AS avg_sentiment,
    ROUND(AVG(e.abnormal_return)::NUMERIC * 100, 3)   AS avg_abnormal_return_pct
FROM earnings_events e
JOIN securities s ON s.ticker = e.ticker
GROUP BY e.ticker, s.name
ORDER BY avg_sentiment DESC;


-- ----6. Biggest overnight reactions (both directions)----
(SELECT 'largest gain' AS kind, ticker, date,
        ROUND(net_sentiment::NUMERIC, 3)            AS net_sentiment,
        ROUND(abnormal_return::NUMERIC * 100, 2)    AS abnormal_return_pct
 FROM earnings_events ORDER BY abnormal_return DESC LIMIT 5)
UNION ALL
(SELECT 'largest drop', ticker, date,
        ROUND(net_sentiment::NUMERIC, 3),
        ROUND(abnormal_return::NUMERIC * 100, 2)
 FROM earnings_events ORDER BY abnormal_return ASC LIMIT 5);


-- ----7. Exploratory: does a CHANGE in tone matter more than the level?----
-- LAG() fetches the same company's previous call. Treat as exploratory.
WITH changes AS (
    SELECT
        ticker, date, abnormal_return,
        net_sentiment
          - LAG(net_sentiment) OVER (PARTITION BY ticker ORDER BY date) AS sentiment_change
    FROM earnings_events
)
SELECT
    COUNT(sentiment_change)                                              AS n,
    ROUND(regr_slope(abnormal_return, sentiment_change)::NUMERIC, 6)     AS slope,
    ROUND(regr_r2(abnormal_return, sentiment_change)::NUMERIC, 6)        AS r_squared
FROM changes
WHERE sentiment_change IS NOT NULL;
