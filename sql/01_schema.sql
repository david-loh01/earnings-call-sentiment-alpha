-- ============================================================
-- 01_schema.sql
-- Creates the four tables for the earnings call project.
--
-- WARNING: this drops and recreates every table, which deletes
-- the data in them. That is safe here because load_db.py can
-- rebuild everything from the JSON files in about a minute.
--
-- Run with:  psql -d earnings_alpha -f sql/01_schema.sql
-- ============================================================

DROP TABLE IF EXISTS sentiment_scores, transcripts, daily_prices, securities CASCADE;


-- ----One row per stock or ETF----
-- XLK (the benchmark) lives here too, flagged with is_benchmark.
CREATE TABLE securities (
    ticker        TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    exchange      TEXT NOT NULL CHECK (exchange IN ('nasdaq', 'nyse', 'nysearca')),
    is_benchmark  BOOLEAN NOT NULL DEFAULT FALSE
);


-- ----One row per ticker per trading day (from Tiingo)----
CREATE TABLE daily_prices (
    ticker      TEXT NOT NULL REFERENCES securities (ticker),
    price_date  DATE NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    adj_open    DOUBLE PRECISION NOT NULL,
    adj_close   DOUBLE PRECISION NOT NULL,
    volume      BIGINT,
    PRIMARY KEY (ticker, price_date)
);


-- ----One row per earnings call----
CREATE TABLE transcripts (
    transcript_id  SERIAL PRIMARY KEY,
    ticker         TEXT NOT NULL REFERENCES securities (ticker),
    call_date      DATE NOT NULL,
    source_url     TEXT,
    cleaned_text   TEXT NOT NULL,
    UNIQUE (ticker, call_date)
);


-- ----One row per scored transcript (FinBERT output)----
CREATE TABLE sentiment_scores (
    transcript_id     INTEGER PRIMARY KEY REFERENCES transcripts (transcript_id) ON DELETE CASCADE,
    net_sentiment     DOUBLE PRECISION NOT NULL,
    avg_positive      DOUBLE PRECISION NOT NULL,
    avg_negative      DOUBLE PRECISION NOT NULL,
    avg_neutral       DOUBLE PRECISION NOT NULL,
    sentences_scored  INTEGER NOT NULL CHECK (sentences_scored >= 0)
);
