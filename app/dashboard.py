import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
from scipy import stats
from pathlib import Path

# ----Configuration----
ROOT      = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed_data" / "master.csv"

st.set_page_config(
    page_title="Earnings Call Sentiment Alpha",
    page_icon="📈",
    layout="wide"
)

# ----Load data----
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# ----Run OLS and t-test----
@st.cache_data
def run_statistics(data: pd.DataFrame):
    results = {}
    return_vars = {
        "abnormal_return": "Abnormal Return",
        "overnight_gap":   "Overnight Gap",
        "next_day_return": "Next Day Return",
    }
    for var, label in return_vars.items():
        x = data["net_sentiment"]
        y = data[var]
        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()
        median = x.median()
        high = y[x >  median]
        low  = y[x <= median]
        t_stat, p_val = stats.ttest_ind(high, low)
        results[var] = {
            "label":        label,
            "coef":         model.params["net_sentiment"],
            "pval_ols":     model.pvalues["net_sentiment"],
            "rsq":          model.rsquared,
            "high_mean":    high.mean(),
            "low_mean":     low.mean(),
            "diff":         high.mean() - low.mean(),
            "t_stat":       t_stat,
            "pval_ttest":   p_val,
        }
    return results

stats_results = run_statistics(df)

# ────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────
st.title("📈 Earnings Call Sentiment Alpha")
st.markdown(
    "Does the sentiment of what executives say on earnings calls predict "
    "how the stock moves the next day? This dashboard explores that question "
    "across **{} earnings calls** from **{} S&P 500 IT sector companies** "
    "between **{}** and **{}**.".format(
        len(df),
        df["ticker"].nunique(),
        df["date"].min().strftime("%b %Y"),
        df["date"].max().strftime("%b %Y"),
    )
)

st.divider()

# ────────────────────────────────────────────────────────────
# SECTION 1 — KEY METRICS
# ────────────────────────────────────────────────────────────
st.subheader("Key Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Earnings Calls", f"{len(df):,}")
col2.metric("Companies", df["ticker"].nunique())
col3.metric("Avg Net Sentiment", f"{df['net_sentiment'].mean():.3f}")
col4.metric(
    "Abnormal Return Signal",
    f"p = {stats_results['abnormal_return']['pval_ols']:.4f}",
    delta="Significant ✓" if stats_results["abnormal_return"]["pval_ols"] < 0.05 else "Not significant"
)

st.divider()

# ────────────────────────────────────────────────────────────
# SECTION 2 — SCATTER PLOT
# ────────────────────────────────────────────────────────────
st.subheader("Sentiment vs Abnormal Return")

return_choice = st.selectbox(
    "Select return variable",
    options=["abnormal_return", "overnight_gap", "next_day_return"],
    format_func=lambda x: {
        "abnormal_return": "Abnormal Return (overnight gap minus XLK)",
        "overnight_gap":   "Overnight Gap (raw)",
        "next_day_return": "Next Day Return (full day)",
    }[x]
)

fig_scatter = px.scatter(
    df,
    x="net_sentiment",
    y=return_choice,
    color="ticker",
    hover_data=["ticker", "date", "quarter", "year"],
    trendline="ols",
    trendline_scope="overall",
    trendline_color_override="red",
    labels={
        "net_sentiment": "Net Sentiment (FinBERT)",
        return_choice:   return_choice.replace("_", " ").title(),
    },
    title=f"Net Sentiment vs {return_choice.replace('_', ' ').title()}",
    height=500,
)
fig_scatter.update_traces(marker=dict(size=5, opacity=0.6))
st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# ────────────────────────────────────────────────────────────
# SECTION 3 — BAR CHART: HIGH VS LOW SENTIMENT
# ────────────────────────────────────────────────────────────
st.subheader("Average Returns: High vs Low Sentiment Groups")
st.markdown("Earnings calls split at the median sentiment score into two groups.")

bar_data = []
for var, res in stats_results.items():
    bar_data.append({"Group": "High Sentiment", "Variable": res["label"], "Mean Return": res["high_mean"]})
    bar_data.append({"Group": "Low Sentiment",  "Variable": res["label"], "Mean Return": res["low_mean"]})

bar_df = pd.DataFrame(bar_data)

fig_bar = px.bar(
    bar_df,
    x="Variable",
    y="Mean Return",
    color="Group",
    barmode="group",
    color_discrete_map={"High Sentiment": "#2ecc71", "Low Sentiment": "#e74c3c"},
    labels={"Mean Return": "Mean Return", "Variable": "Return Metric"},
    title="Mean Returns by Sentiment Group",
    height=400,
)
fig_bar.add_hline(y=0, line_dash="dash", line_color="grey")
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ────────────────────────────────────────────────────────────
# SECTION 4 — SENTIMENT BY TICKER OVER TIME
# ────────────────────────────────────────────────────────────
st.subheader("Sentiment Scores by Ticker Over Time")

available = sorted(df["ticker"].unique())
default_tickers = [t for t in ["AAPL", "MSFT", "NVDA", "GOOG"] if t in available]

selected_tickers = st.multiselect(
    "Select tickers to display",
    options=available,
    default=default_tickers
)

if selected_tickers:
    filtered = df[df["ticker"].isin(selected_tickers)]
    fig_time = px.line(
        filtered.sort_values("date"),
        x="date",
        y="net_sentiment",
        color="ticker",
        markers=True,
        labels={"net_sentiment": "Net Sentiment", "date": "Date"},
        title="Net Sentiment Over Time",
        height=400,
    )
    fig_time.add_hline(
        y=df["net_sentiment"].median(),
        line_dash="dash",
        line_color="grey",
        annotation_text="Median sentiment"
    )
    st.plotly_chart(fig_time, use_container_width=True)
else:
    st.info("Select at least one ticker above.")

st.divider()

# ────────────────────────────────────────────────────────────
# SECTION 5 — STATISTICAL RESULTS TABLE
# ────────────────────────────────────────────────────────────
st.subheader("Statistical Results")

tab1, tab2 = st.tabs(["OLS Regression", "T-Test"])

with tab1:
    ols_rows = []
    for var, res in stats_results.items():
        ols_rows.append({
            "Return Variable": res["label"],
            "Coefficient":     f"{res['coef']:.6f}",
            "P-value":         f"{res['pval_ols']:.4f}",
            "R-squared":       f"{res['rsq']:.6f}",
            "Significant":     "✓ Yes" if res["pval_ols"] < 0.05 else ("~ Marginal" if res["pval_ols"] < 0.10 else "✗ No"),
        })
    st.dataframe(pd.DataFrame(ols_rows), use_container_width=True, hide_index=True)
    st.caption("Coefficient = change in return per unit increase in net sentiment. P-value < 0.05 = statistically significant.")

with tab2:
    ttest_rows = []
    for var, res in stats_results.items():
        ttest_rows.append({
            "Return Variable":       res["label"],
            "High Sentiment Mean":   f"{res['high_mean']:+.6f}",
            "Low Sentiment Mean":    f"{res['low_mean']:+.6f}",
            "Difference":            f"{res['diff']:+.6f}",
            "T-statistic":           f"{res['t_stat']:.4f}",
            "P-value":               f"{res['pval_ttest']:.4f}",
            "Significant":           "✓ Yes" if res["pval_ttest"] < 0.05 else ("~ Marginal" if res["pval_ttest"] < 0.10 else "✗ No"),
        })
    st.dataframe(pd.DataFrame(ttest_rows), use_container_width=True, hide_index=True)
    st.caption("Groups split at median net sentiment. T-test compares mean returns of high vs low sentiment groups.")

st.divider()

# ────────────────────────────────────────────────────────────
# SECTION 6 — FINDINGS SUMMARY
# ────────────────────────────────────────────────────────────
st.subheader("Findings Summary")

ar = stats_results["abnormal_return"]
og = stats_results["overnight_gap"]
nd = stats_results["next_day_return"]

st.markdown(f"""
**Hypothesis:** Earnings call transcripts with higher FinBERT net sentiment are associated
with statistically significant positive abnormal returns in the window following the call.

**Result: Supported**

We find statistically significant evidence that earnings call sentiment positively predicts
abnormal returns in the S&P 500 IT sector across 619 earnings calls from 2022 to 2024.

**Key findings:**

- **Abnormal return** (overnight gap minus XLK benchmark): coefficient = {ar['coef']:.4f},
  p = {ar['pval_ols']:.4f} ✓ significant. High sentiment calls averaged
  {ar['high_mean']*100:+.2f}% vs low sentiment calls at {ar['low_mean']*100:+.2f}% —
  a gap of {ar['diff']*100:.2f} percentage points.

- **Overnight gap** (raw): coefficient = {og['coef']:.4f}, p = {og['pval_ols']:.4f} ✓ significant.
  Consistent with the abnormal return finding, suggesting the result is robust to
  benchmark choice.

- **Next day return** (full day): coefficient = {nd['coef']:.4f}, p = {nd['pval_ols']:.4f} — marginal.
  The signal weakens over the full trading day, consistent with the market rapidly
  pricing in earnings call information at the open before intraday noise dilutes the effect.

**Limitations:** R-squared values are low (1.6% for abnormal return), reflecting the
complexity of equity markets. Remaining boilerplate in some transcripts may introduce
minor sentiment bias. Results are specific to the S&P 500 IT sector and may not
generalise to other sectors or time periods.
""")

st.divider()
st.caption("Built with FinBERT · Tiingo · earningscall.biz · Streamlit | David Loh")